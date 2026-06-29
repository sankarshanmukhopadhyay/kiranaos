"""
ingestion.py — Core business logic for the order lifecycle.

This module owns:
  - find_or_create_customer (upsert on phone, pattern from uploaded app)
  - ingest_message (parse → create order → update customer)
  - order CRUD and status transitions
  - credit/udhaari ledger (expanded from KiranaOS v1)
  - dashboard_summary and analytics queries
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.domain import (
    Customer,
    InboundMessage,
    LedgerEntry,
    MessageType,
    Order,
    OrderItem,
    OrderStatus,
    ParseStatus,
)
from app.schemas.domain import (
    AmountUpdateIn,
    CreditAdjustIn,
    CustomerCreateIn,
    IngestMessageIn,
)
from app.services.adapters import extract_items_with_openai
from app.services.parser import parse_order_text
from app.services.auth import ensure_default_store
from app.services.security import validate_external_media_url

logger = logging.getLogger(__name__)

DORMANT_DAYS = 14


# ── Helpers ───────────────────────────────────────────────────────────────────

def dormant_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=DORMANT_DAYS)


def _is_dormant(last_order_at: datetime | None) -> bool:
    if last_order_at is None:
        return True
    ts = last_order_at if last_order_at.tzinfo else last_order_at.replace(tzinfo=timezone.utc)
    return ts < dormant_cutoff()


# ── Customer ──────────────────────────────────────────────────────────────────

def _store_id(payload_store_id: int | None = None) -> int:
    return payload_store_id or get_settings().default_store_id


def find_or_create_customer(db: Session, payload: IngestMessageIn, store_id: int | None = None) -> Customer:
    """
    Upsert on phone number. Updates name/building if previously unknown.
    Never overwrites an existing real name with 'Unknown customer'.
    """
    ensure_default_store(db)
    scoped_store_id = _store_id(store_id or payload.store_id)
    customer = db.scalar(
        select(Customer).where(Customer.store_id == scoped_store_id, Customer.phone == payload.phone)
    )

    if customer:
        if payload.customer_name and customer.name == "Unknown customer":
            customer.name = payload.customer_name
        if payload.building and not customer.building:
            customer.building = payload.building
        if payload.language and not customer.language_hint:
            customer.language_hint = payload.language
        return customer

    customer = Customer(
        store_id=scoped_store_id,
        phone=payload.phone,
        name=payload.customer_name or "Unknown customer",
        building=payload.building,
        language_hint=payload.language,
    )
    db.add(customer)
    db.flush()
    logger.info("New customer created: %s (%s)", customer.name, customer.phone)
    return customer


def create_customer(db: Session, data: CustomerCreateIn, store_id: int | None = None) -> Customer:
    ensure_default_store(db)
    scoped_store_id = _store_id(store_id or data.store_id)
    existing = db.scalar(
        select(Customer).where(Customer.store_id == scoped_store_id, Customer.phone == data.phone)
    )
    if existing:
        raise ValueError(f"Phone {data.phone} already registered to customer {existing.id}")
    customer = Customer(
        store_id=scoped_store_id,
        name=data.name,
        phone=data.phone,
        building=data.building,
        language_hint=data.language_hint,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int, store_id: int | None = None) -> Customer:
    stmt = select(Customer).where(Customer.id == customer_id)
    if store_id is not None:
        stmt = stmt.where(Customer.store_id == store_id)
    c = db.scalar(stmt)
    if not c:
        raise ValueError(f"Customer {customer_id} not found")
    return c


def list_customers(db: Session, dormant_only: bool = False, store_id: int | None = None) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.name)
    if store_id is not None:
        stmt = stmt.where(Customer.store_id == store_id)
    if dormant_only:
        stmt = stmt.where(
            (Customer.last_order_at.is_(None))
            | (Customer.last_order_at < dormant_cutoff())
        )
    return list(db.scalars(stmt).all())


def get_customer_with_dormant(db: Session, customer_id: int, store_id: int | None = None) -> tuple[Customer, bool]:
    c = get_customer(db, customer_id, store_id=store_id)
    return c, _is_dormant(c.last_order_at)


# ── Message ingestion ─────────────────────────────────────────────────────────

async def ingest_message(db: Session, payload: IngestMessageIn) -> Order:
    """
    Full ingestion pipeline:
      1. Upsert customer.
      2. Store raw InboundMessage.
      3. Run OCR if image/voice and media_url is set.
      4. Parse text into items.
      5. Create Order + OrderItems.
      6. Update customer.last_order_at.
    """
    ensure_default_store(db)
    scoped_store_id = _store_id(payload.store_id)
    customer = find_or_create_customer(db, payload, store_id=scoped_store_id)

    text = payload.text

    # OCR / transcription adapter — only runs if configured
    if not text and payload.media_url:
        try:
            validate_external_media_url(payload.media_url)
        except ValueError as exc:
            logger.warning("Rejected unsafe media URL: %s", exc)
            payload.media_url = None

    if not text and payload.media_url:
        if payload.message_type == MessageType.image:
            try:
                from app.services.ocr.google_vision import extract_text
                text = await extract_text(payload.media_url)
            except Exception as exc:
                logger.warning("OCR unavailable: %s", exc)
        elif payload.message_type == MessageType.voice:
            from app.services.voice import transcribe_voice_note
            text = await transcribe_voice_note(payload.media_url, payload.media_type)
            if not text:
                logger.info("Voice transcription not configured or failed — order set to needs_review")

    message = InboundMessage(
        customer_id=customer.id,
        store_id=scoped_store_id,
        source=payload.source,
        external_message_id=payload.external_message_id,
        message_type=payload.message_type,
        raw_text=payload.text,
        extracted_text=text,
        media_url=payload.media_url,
        media_type=payload.media_type,
        language=payload.language,
    )
    db.add(message)
    db.flush()

    parsed_items = parse_order_text(text)
    if text and not parsed_items:
        ai_items = extract_items_with_openai(text)
        if ai_items:
            parsed_items = parse_order_text("\n".join(ai_items))
    status = OrderStatus.pending if parsed_items else OrderStatus.needs_review
    message.parse_status = ParseStatus.parsed if parsed_items else ParseStatus.needs_review

    notes: str | None = None
    if not parsed_items:
        if payload.message_type == MessageType.image:
            notes = "Image received. Configure Google Vision OCR to auto-extract items."
        elif payload.message_type == MessageType.voice:
            notes = "Voice note received. Configure a transcription adapter to auto-extract items."
        else:
            notes = "No items could be parsed. Please review manually."

    order = Order(
        customer_id=customer.id,
        store_id=scoped_store_id,
        message_id=message.id,
        status=status,
        notes=notes,
    )
    db.add(order)
    db.flush()

    for item in parsed_items:
        db.add(OrderItem(
            order_id=order.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            confidence=item.confidence,
        ))

    customer.last_order_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(
        "Order %s created for customer %s (%d items, status=%s)",
        order.id, customer.id, len(parsed_items), status,
    )
    return _load_order(db, order.id)


# ── Order queries ─────────────────────────────────────────────────────────────

def _load_order(db: Session, order_id: int, store_id: int | None = None) -> Order:
    stmt = select(Order).where(Order.id == order_id)
    if store_id is not None:
        stmt = stmt.where(Order.store_id == store_id)
    order = db.scalar(
        stmt
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
    )
    if not order:
        raise ValueError(f"Order {order_id} not found")
    return order


def get_order(db: Session, order_id: int, store_id: int | None = None) -> Order:
    return _load_order(db, order_id, store_id=store_id)


def list_orders(
    db: Session,
    status: OrderStatus | None = None,
    customer_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    store_id: int | None = None,
) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(Order.status == status)
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    if store_id is not None:
        stmt = stmt.where(Order.store_id == store_id)
    return list(db.scalars(stmt).all())


def update_order_status(db: Session, order_id: int, status: OrderStatus, store_id: int | None = None) -> Order:
    order = _load_order(db, order_id, store_id=store_id)
    order.status = status
    if status == OrderStatus.delivered:
        order.delivered_at = datetime.now(timezone.utc)
    db.commit()
    return _load_order(db, order_id, store_id=store_id)


def update_order_amount(db: Session, order_id: int, data: AmountUpdateIn, store_id: int | None = None) -> Order:
    order = _load_order(db, order_id, store_id=store_id)
    order.amount_due = data.amount_due
    order.is_credit  = data.is_credit
    db.commit()
    return _load_order(db, order_id, store_id=store_id)


# ── Udhaari / credit ledger ───────────────────────────────────────────────────

def adjust_credit(db: Session, customer_id: int, data: CreditAdjustIn, store_id: int | None = None) -> Customer:
    """
    Record a credit adjustment. Positive = udhaari extended. Negative = payment received.
    Prevents the balance from going below zero on payment (you cannot collect more than owed).
    """
    customer = get_customer(db, customer_id, store_id=store_id)

    if data.amount < 0:
        # Payment — cap at what's actually owed
        actual = max(data.amount, -customer.credit_balance)
    else:
        actual = data.amount

    customer.credit_balance = round(customer.credit_balance + actual, 2)
    db.add(LedgerEntry(
        customer_id=customer_id,
        store_id=customer.store_id,
        amount=actual,
        reason=data.reason,
    ))
    db.commit()
    db.refresh(customer)
    logger.info(
        "Credit adjusted for customer %s: %+.2f (balance now %.2f)",
        customer_id, actual, customer.credit_balance,
    )
    return customer


def get_ledger(db: Session, customer_id: int, store_id: int | None = None) -> list[LedgerEntry]:
    get_customer(db, customer_id, store_id=store_id)
    return list(db.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.customer_id == customer_id)
        .where(LedgerEntry.store_id == store_id if store_id is not None else True)
        .order_by(LedgerEntry.created_at.desc())
    ).all())


# ── Dashboard summary ─────────────────────────────────────────────────────────

def dashboard_summary(db: Session, store_id: int | None = None) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    status_counts = dict(
        db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.store_id == store_id if store_id is not None else True)
            .group_by(Order.status)
        ).all()
    )

    dormant = db.scalar(
        select(func.count(Customer.id)).where(
            (Customer.store_id == store_id if store_id is not None else True),
            (Customer.last_order_at.is_(None))
            | (Customer.last_order_at < dormant_cutoff())
        )
    ) or 0

    delivered_today = db.scalar(
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.delivered,
            Order.store_id == store_id if store_id is not None else True,
            Order.delivered_at >= today_start,
        )
    ) or 0

    total_credit = db.scalar(
        select(func.coalesce(func.sum(Customer.credit_balance), 0.0))
        .where(Customer.store_id == store_id if store_id is not None else True)
    ) or 0.0

    return {
        "pending":           status_counts.get(OrderStatus.pending, 0),
        "packed":            status_counts.get(OrderStatus.packed, 0),
        "delivered_today":   delivered_today,
        "needs_review":      status_counts.get(OrderStatus.needs_review, 0),
        "dormant_customers": dormant,
        "total_credit":      total_credit,
    }


# ── Analytics ─────────────────────────────────────────────────────────────────

def daily_metrics(db: Session, days: int = 7, store_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.amount_due), 0.0).label("revenue"),
        )
        .where(
            Order.created_at >= cutoff,
            Order.status != OrderStatus.cancelled,
            Order.store_id == store_id if store_id is not None else True,
        )
        .group_by("day")
        .order_by("day")
    ).all()
    return [{"day": str(r.day), "orders": r.orders, "revenue": float(r.revenue)} for r in rows]


def top_items(db: Session, days: int = 30, limit: int = 10, store_id: int | None = None) -> list[dict]:
    """
    Uses the normalised order_items table — not possible with JSON blob storage.
    Returns item name, order count, and total quantity ordered.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            OrderItem.name,
            func.count(OrderItem.id).label("count"),
            func.sum(OrderItem.quantity).label("total_quantity"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.created_at >= cutoff,
            Order.status != OrderStatus.cancelled,
            Order.store_id == store_id if store_id is not None else True,
        )
        .group_by(OrderItem.name)
        .order_by(func.count(OrderItem.id).desc())
        .limit(limit)
    ).all()
    return [
        {"name": r.name, "count": r.count, "total_quantity": float(r.total_quantity)}
        for r in rows
    ]


def input_method_stats(db: Session, days: int = 30, store_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            InboundMessage.message_type,
            func.count(InboundMessage.id).label("count"),
        )
        .where(
            InboundMessage.received_at >= cutoff,
            InboundMessage.store_id == store_id if store_id is not None else True,
        )
        .group_by(InboundMessage.message_type)
        .order_by(func.count(InboundMessage.id).desc())
    ).all()
    return [{"message_type": str(r.message_type), "count": r.count} for r in rows]
