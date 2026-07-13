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
    AuditAction,
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
    CustomerUpdateIn,
    IngestMessageIn,
    OrderCorrectionIn,
    OrderReviewResolveIn,
)
from app.services.adapters import extract_items_with_ai
from app.services.audit import record_audit_event
from app.services.auth import ensure_default_store
from app.services.parser import parse_order_text
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
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
        language_hint=data.language_hint,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer_id: int, data: CustomerUpdateIn, store_id: int | None = None) -> Customer:
    customer = get_customer(db, customer_id, store_id=store_id)
    before = {
        "name": customer.name,
        "building": customer.building,
        "address": customer.address,
        "language_hint": customer.language_hint,
    }
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(customer, key, value)
    record_audit_event(
        db,
        store_id=customer.store_id,
        action=AuditAction.customer_updated,
        entity_type="customer",
        entity_id=customer.id,
        evidence={"from": before, "to": updates},
    )
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

    if payload.external_message_id:
        existing_message = db.scalar(
            select(InboundMessage).where(
                InboundMessage.store_id == scoped_store_id,
                InboundMessage.source == payload.source,
                InboundMessage.external_message_id == payload.external_message_id,
            )
        )
        if existing_message and existing_message.order:
            record_audit_event(
                db,
                store_id=scoped_store_id,
                action=AuditAction.duplicate_message_ignored,
                entity_type="inbound_message",
                entity_id=existing_message.id,
                evidence={"source": payload.source, "external_message_id": payload.external_message_id},
            )
            db.commit()
            return _load_order(db, existing_message.order.id, store_id=scoped_store_id)

    text = payload.text
    parse_failure_reason: str | None = None

    # OCR / transcription adapter — only runs if configured
    if not text and payload.media_url:
        try:
            validate_external_media_url(payload.media_url)
        except ValueError as exc:
            logger.warning("Rejected unsafe media URL: %s", exc)
            parse_failure_reason = "unsafe_media_url"
            payload.media_url = None

    if not text and payload.media_url:
        if payload.message_type == MessageType.image:
            try:
                provider = get_settings().ocr_provider
                if provider == "sarvam":
                    from app.services.ocr.sarvam_vision import extract_text as sarvam_extract_text
                    text = await sarvam_extract_text(payload.media_url)
                elif provider == "google_vision":
                    from app.services.ocr.google_vision import extract_text as google_extract_text
                    text = await google_extract_text(payload.media_url)
                else:
                    text = None
                if not text:
                    parse_failure_reason = "ocr_failed_or_unconfigured"
            except Exception as exc:
                parse_failure_reason = "ocr_failed"
                logger.warning("OCR unavailable: %s", exc)
        elif payload.message_type == MessageType.voice:
            from app.services.voice import transcribe_voice_note
            text = await transcribe_voice_note(payload.media_url, payload.media_type)
            if not text:
                parse_failure_reason = "stt_failed_or_unconfigured"
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
        parse_failure_reason=parse_failure_reason,
    )
    db.add(message)
    db.flush()

    parsed_items = parse_order_text(text)
    if text and not parsed_items:
        ai_items = extract_items_with_ai(text)
        if ai_items:
            parsed_items = parse_order_text("\n".join(ai_items))

    threshold = get_settings().parse_confidence_threshold
    low_confidence = bool(parsed_items) and any(item.confidence < threshold for item in parsed_items)
    status = OrderStatus.pending if parsed_items else OrderStatus.needs_review
    message.parse_status = ParseStatus.parsed if parsed_items else ParseStatus.needs_review
    if low_confidence and not parse_failure_reason:
        parse_failure_reason = "low_confidence_parse"
        message.parse_failure_reason = parse_failure_reason

    notes: str | None = None
    if low_confidence:
        notes = "Low-confidence item detected. Verify before packing."
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
            selectinload(Order.message),
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
        .options(selectinload(Order.customer), selectinload(Order.items), selectinload(Order.message))
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


ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.needs_review: {OrderStatus.pending, OrderStatus.cancelled},
    OrderStatus.pending: {OrderStatus.packed, OrderStatus.cancelled, OrderStatus.needs_review},
    OrderStatus.packed: {OrderStatus.delivered, OrderStatus.cancelled},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}


def _assert_transition_allowed(current: OrderStatus, target: OrderStatus) -> None:
    if current == target:
        return
    if target not in ALLOWED_ORDER_TRANSITIONS[current]:
        raise ValueError(f"Invalid order transition: {current} -> {target}")


def update_order_status(db: Session, order_id: int, status: OrderStatus, store_id: int | None = None) -> Order:
    order = _load_order(db, order_id, store_id=store_id)
    previous = order.status
    _assert_transition_allowed(previous, status)
    order.status = status
    if status == OrderStatus.delivered:
        order.delivered_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        store_id=order.store_id,
        action=AuditAction.order_status_updated,
        entity_type="order",
        entity_id=order.id,
        evidence={"from": str(previous), "to": str(status)},
    )
    db.commit()
    return _load_order(db, order_id, store_id=store_id)


def correct_order_items(db: Session, order_id: int, data: OrderCorrectionIn, store_id: int | None = None) -> Order:
    order = _load_order(db, order_id, store_id=store_id)
    before = [
        {"id": item.id, "name": item.name, "quantity": item.quantity, "unit": item.unit, "confidence": item.confidence}
        for item in order.items
    ]
    for item in list(order.items):
        db.delete(item)
    db.flush()
    for correction_item in data.items:
        db.add(OrderItem(
            order_id=order.id,
            name=correction_item.name,
            quantity=correction_item.quantity,
            unit=correction_item.unit,
            confidence=correction_item.confidence,
        ))
    if data.notes is not None:
        order.notes = data.notes
    record_audit_event(
        db,
        store_id=order.store_id,
        action=AuditAction.order_items_corrected,
        entity_type="order",
        entity_id=order.id,
        evidence={"from": before, "to": [item.model_dump() for item in data.items]},
    )
    db.commit()
    db.expire_all()
    return _load_order(db, order_id, store_id=store_id)


def resolve_order_review(db: Session, order_id: int, data: OrderReviewResolveIn, store_id: int | None = None) -> Order:
    if data.status not in {OrderStatus.pending, OrderStatus.cancelled}:
        raise ValueError("Review can only resolve an order to pending or cancelled")
    correction = OrderCorrectionIn(items=data.items, notes=data.notes)
    order = correct_order_items(db, order_id, correction, store_id=store_id)
    previous = order.status
    _assert_transition_allowed(previous, data.status)
    order.status = data.status
    if order.message:
        order.message.parse_status = ParseStatus.parsed if data.items else ParseStatus.needs_review
        order.message.parse_failure_reason = None if data.items else order.message.parse_failure_reason
    record_audit_event(
        db,
        store_id=order.store_id,
        action=AuditAction.order_review_resolved,
        entity_type="order",
        entity_id=order.id,
        evidence={"from": str(previous), "to": str(data.status), "items": [item.model_dump() for item in data.items]},
    )
    db.commit()
    db.expire_all()
    return _load_order(db, order_id, store_id=store_id)


def update_order_amount(db: Session, order_id: int, data: AmountUpdateIn, store_id: int | None = None) -> Order:
    order = _load_order(db, order_id, store_id=store_id)
    previous = {"amount_due": order.amount_due, "is_credit": bool(order.is_credit)}
    order.amount_due = data.amount_due
    order.is_credit  = data.is_credit
    record_audit_event(
        db,
        store_id=order.store_id,
        action=AuditAction.order_amount_updated,
        entity_type="order",
        entity_id=order.id,
        evidence={"from": previous, "to": data.model_dump()},
    )
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
    record_audit_event(
        db,
        store_id=customer.store_id,
        action=AuditAction.credit_adjusted,
        entity_type="customer",
        entity_id=customer.id,
        evidence={"amount": actual, "reason": data.reason, "balance": customer.credit_balance},
    )
    db.commit()
    db.refresh(customer)
    logger.info(
        "Credit adjusted for customer %s: %+.2f (balance now %.2f)",
        customer_id, actual, customer.credit_balance,
    )
    return customer


def get_ledger(db: Session, customer_id: int, store_id: int | None = None) -> list[LedgerEntry]:
    get_customer(db, customer_id, store_id=store_id)
    stmt = select(LedgerEntry).where(LedgerEntry.customer_id == customer_id)
    if store_id is not None:
        stmt = stmt.where(LedgerEntry.store_id == store_id)
    return list(db.scalars(stmt.order_by(LedgerEntry.created_at.desc())).all())


# ── Dashboard summary ─────────────────────────────────────────────────────────

def dashboard_summary(db: Session, store_id: int | None = None) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    status_stmt = select(Order.status, func.count(Order.id)).group_by(Order.status)
    if store_id is not None:
        status_stmt = status_stmt.where(Order.store_id == store_id)
    status_counts: dict[OrderStatus, int] = {status: count for status, count in db.execute(status_stmt).all()}

    dormant_stmt = select(func.count(Customer.id)).where(
        (Customer.last_order_at.is_(None)) | (Customer.last_order_at < dormant_cutoff())
    )
    if store_id is not None:
        dormant_stmt = dormant_stmt.where(Customer.store_id == store_id)
    dormant = db.scalar(dormant_stmt) or 0

    delivered_stmt = select(func.count(Order.id)).where(
        Order.status == OrderStatus.delivered,
        Order.delivered_at >= today_start,
    )
    if store_id is not None:
        delivered_stmt = delivered_stmt.where(Order.store_id == store_id)
    delivered_today = db.scalar(delivered_stmt) or 0

    credit_stmt = select(func.coalesce(func.sum(Customer.credit_balance), 0.0))
    if store_id is not None:
        credit_stmt = credit_stmt.where(Customer.store_id == store_id)
    total_credit = db.scalar(credit_stmt) or 0.0

    return {
        "pending":           status_counts.get(OrderStatus.pending, 0),
        "packed":            status_counts.get(OrderStatus.packed, 0),
        "delivered_today":   delivered_today,
        "needs_review":      status_counts.get(OrderStatus.needs_review, 0),
        "dormant_customers": dormant,
        "total_credit":      total_credit,
    }


def daily_closing(db: Session, store_id: int, day: str | None = None) -> dict:
    if day:
        start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    rows = list(db.scalars(select(Order).where(Order.store_id == store_id, Order.created_at >= start, Order.created_at < end)).all())
    return {
        "store_id": store_id,
        "day": start.date().isoformat(),
        "orders_created": len(rows),
        "delivered": sum(1 for o in rows if o.status == OrderStatus.delivered),
        "cancelled": sum(1 for o in rows if o.status == OrderStatus.cancelled),
        "needs_review": sum(1 for o in rows if o.status == OrderStatus.needs_review),
        "amount_due_total": float(sum(o.amount_due for o in rows)),
        "credit_extended_total": float(sum(o.amount_due for o in rows if o.is_credit)),
    }


# ── Analytics ─────────────────────────────────────────────────────────────────

def daily_metrics(db: Session, days: int = 7, store_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    metrics_stmt = (
        select(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.amount_due), 0.0).label("revenue"),
        )
        .where(Order.created_at >= cutoff, Order.status != OrderStatus.cancelled)
        .group_by("day")
        .order_by("day")
    )
    if store_id is not None:
        metrics_stmt = metrics_stmt.where(Order.store_id == store_id)
    rows = db.execute(metrics_stmt).all()
    return [{"day": str(r.day), "orders": r.orders, "revenue": float(r.revenue)} for r in rows]


def top_items(db: Session, days: int = 30, limit: int = 10, store_id: int | None = None) -> list[dict]:
    """
    Uses the normalised order_items table — not possible with JSON blob storage.
    Returns item name, order count, and total quantity ordered.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    top_items_stmt = (
        select(
            OrderItem.name,
            func.count(OrderItem.id).label("count"),
            func.sum(OrderItem.quantity).label("total_quantity"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= cutoff, Order.status != OrderStatus.cancelled)
        .group_by(OrderItem.name)
        .order_by(func.count(OrderItem.id).desc())
        .limit(limit)
    )
    if store_id is not None:
        top_items_stmt = top_items_stmt.where(Order.store_id == store_id)
    rows = db.execute(top_items_stmt).all()
    return [
        {"name": r.name, "count": r.count, "total_quantity": float(r.total_quantity)}
        for r in rows
    ]


def input_method_stats(db: Session, days: int = 30, store_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    input_stmt = (
        select(
            InboundMessage.message_type,
            func.count(InboundMessage.id).label("count"),
        )
        .where(InboundMessage.received_at >= cutoff)
        .group_by(InboundMessage.message_type)
        .order_by(func.count(InboundMessage.id).desc())
    )
    if store_id is not None:
        input_stmt = input_stmt.where(InboundMessage.store_id == store_id)
    rows = db.execute(input_stmt).all()
    return [{"message_type": str(r.message_type), "count": r.count} for r in rows]
