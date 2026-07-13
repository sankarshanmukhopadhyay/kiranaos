import json
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.domain import (
    AuditAction,
    Customer,
    DeliveryAgent,
    DeliveryAssignment,
    DeliveryStatus,
    LedgerEntry,
    Order,
    OrderStatus,
    OutboundMessage,
    OutboundStatus,
    Payment,
    PaymentStatus,
)
from app.schemas.domain import (
    DeliveryAgentCreateIn,
    DeliveryAssignmentIn,
    OutboundConfirmationIn,
    UpiWebhookIn,
)
from app.services.adapters import send_meta_whatsapp, send_twilio_whatsapp
from app.services.audit import record_audit_event


def create_outbound_confirmation(
    db: Session,
    order: Order,
    payload: OutboundConfirmationIn,
) -> OutboundMessage:
    customer = order.customer
    body = payload.body or f"Order #{order.id} is {order.status}. Thank you for ordering from KiranaOS."
    outbound = OutboundMessage(
        store_id=order.store_id,
        order_id=order.id,
        customer_id=customer.id,
        destination_phone=customer.phone,
        body=body,
        provider="simulation",
        status=OutboundStatus.simulated,
        sent_at=datetime.now(timezone.utc),
    )
    settings = get_settings()
    provider = settings.whatsapp_provider.lower()
    outbound.provider = provider
    outbound.dispatch_attempts = 1
    if provider == "simulation":
        outbound.status = OutboundStatus.simulated
        outbound.sent_at = datetime.now(timezone.utc)
    else:
        try:
            if provider == "twilio":
                outbound.provider_message_id = send_twilio_whatsapp(customer.phone, body)
            elif provider == "meta":
                outbound.provider_message_id = send_meta_whatsapp(customer.phone, body)
            else:
                raise RuntimeError(f"Unsupported WhatsApp provider: {provider}")
            outbound.status = OutboundStatus.sent
            outbound.sent_at = datetime.now(timezone.utc)
        except Exception as exc:
            outbound.status = OutboundStatus.failed
            outbound.failure_reason = str(exc)
    db.add(outbound)
    db.flush()
    record_audit_event(
        db,
        store_id=order.store_id,
        action=AuditAction.outbound_confirmation_created,
        entity_type="outbound_message",
        entity_id=outbound.id,
        evidence={"order_id": order.id, "provider": outbound.provider, "status": str(outbound.status)},
    )
    db.commit()
    db.refresh(outbound)
    return outbound


def create_delivery_agent(db: Session, store_id: int, payload: DeliveryAgentCreateIn) -> DeliveryAgent:
    agent = DeliveryAgent(
        store_id=store_id,
        name=payload.name,
        phone=payload.phone,
        active=payload.active,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def list_delivery_agents(db: Session, store_id: int) -> list[DeliveryAgent]:
    return list(
        db.scalars(
            select(DeliveryAgent)
            .where(DeliveryAgent.store_id == store_id)
            .order_by(DeliveryAgent.name)
        ).all()
    )


def assign_delivery(
    db: Session,
    store_id: int,
    order_id: int,
    payload: DeliveryAssignmentIn,
) -> DeliveryAssignment:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.store_id == store_id))
    if not order:
        raise ValueError(f"Order {order_id} not found")
    agent = db.scalar(
        select(DeliveryAgent).where(
            DeliveryAgent.id == payload.agent_id,
            DeliveryAgent.store_id == store_id,
            DeliveryAgent.active == True,  # noqa: E712
        )
    )
    if not agent:
        raise ValueError(f"Delivery agent {payload.agent_id} not found")

    assignment = db.scalar(
        select(DeliveryAssignment).where(DeliveryAssignment.order_id == order_id)
    )
    if assignment:
        assignment.agent_id = payload.agent_id
        assignment.route_order = payload.route_order
        assignment.notes = payload.notes
        assignment.status = DeliveryStatus.assigned
    else:
        assignment = DeliveryAssignment(
            store_id=store_id,
            order_id=order_id,
            agent_id=payload.agent_id,
            route_order=payload.route_order,
            notes=payload.notes,
        )
        db.add(assignment)
    record_audit_event(
        db,
        store_id=store_id,
        action=AuditAction.delivery_assigned,
        entity_type="order",
        entity_id=order_id,
        evidence={"agent_id": payload.agent_id, "route_order": payload.route_order},
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def update_delivery_status(
    db: Session,
    store_id: int,
    assignment_id: int,
    status: DeliveryStatus,
) -> DeliveryAssignment:
    assignment = db.scalar(
        select(DeliveryAssignment).where(
            DeliveryAssignment.id == assignment_id,
            DeliveryAssignment.store_id == store_id,
        )
    )
    if not assignment:
        raise ValueError(f"Delivery assignment {assignment_id} not found")
    assignment.status = status
    if status == DeliveryStatus.delivered:
        order = db.scalar(select(Order).where(Order.id == assignment.order_id, Order.store_id == store_id))
        if order:
            order.status = OrderStatus.delivered
            order.delivered_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        store_id=store_id,
        action=AuditAction.delivery_status_updated,
        entity_type="delivery_assignment",
        entity_id=assignment.id,
        evidence={"status": str(status), "order_id": assignment.order_id},
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def route_for_agent(db: Session, store_id: int, agent_id: int) -> list[dict]:
    rows = db.scalars(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.store_id == store_id,
            DeliveryAssignment.agent_id == agent_id,
            DeliveryAssignment.status.in_([DeliveryStatus.assigned, DeliveryStatus.picked_up]),
        )
        .options(
            selectinload(DeliveryAssignment.order).selectinload(Order.customer),
        )
        .order_by(DeliveryAssignment.route_order, DeliveryAssignment.assigned_at)
    ).all()
    return [
        {
            "assignment_id": row.id,
            "order_id": row.order_id,
            "customer_name": row.order.customer.name,
            "phone": row.order.customer.phone,
            "building": row.order.customer.building,
            "address": row.order.customer.address,
            "latitude": row.order.customer.latitude,
            "longitude": row.order.customer.longitude,
            "route_order": row.route_order,
            "status": row.status,
        }
        for row in rows
    ]


def _distance(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    return math.hypot(a_lat - b_lat, a_lon - b_lon)


def optimize_route(
    db: Session,
    store_id: int,
    *,
    agent_id: int | None = None,
    order_ids: list[int] | None = None,
    start_latitude: float | None = None,
    start_longitude: float | None = None,
) -> dict:
    stmt = (
        select(DeliveryAssignment)
        .where(DeliveryAssignment.store_id == store_id)
        .options(selectinload(DeliveryAssignment.order).selectinload(Order.customer))
    )
    if agent_id is not None:
        stmt = stmt.where(DeliveryAssignment.agent_id == agent_id)
    if order_ids:
        stmt = stmt.where(DeliveryAssignment.order_id.in_(order_ids))
    assignments = list(db.scalars(stmt).all())

    geocoded = [
        row for row in assignments
        if row.order.customer.latitude is not None and row.order.customer.longitude is not None
    ]
    if geocoded and len(geocoded) == len(assignments):
        first_lat = geocoded[0].order.customer.latitude
        first_lon = geocoded[0].order.customer.longitude
        assert first_lat is not None
        assert first_lon is not None
        current_lat = float(start_latitude if start_latitude is not None else first_lat)
        current_lon = float(start_longitude if start_longitude is not None else first_lon)
        remaining = geocoded[:]
        ordered: list[DeliveryAssignment] = []
        while remaining:
            next_stop = min(
                remaining,
                key=lambda row: _distance(
                    current_lat,
                    current_lon,
                    float(row.order.customer.latitude if row.order.customer.latitude is not None else current_lat),
                    float(row.order.customer.longitude if row.order.customer.longitude is not None else current_lon),
                ),
            )
            ordered.append(next_stop)
            remaining.remove(next_stop)
            current_lat = float(next_stop.order.customer.latitude if next_stop.order.customer.latitude is not None else current_lat)
            current_lon = float(next_stop.order.customer.longitude if next_stop.order.customer.longitude is not None else current_lon)
        strategy = "nearest_neighbor_geocoded"
    else:
        ordered = sorted(
            assignments,
            key=lambda row: (
                row.order.customer.building or "",
                row.order.customer.address or "",
                row.order.customer.name,
                row.order_id,
            ),
        )
        strategy = "address_sort_fallback"

    stops = []
    for idx, assignment in enumerate(ordered, start=1):
        assignment.route_order = idx
        stops.append({
            "assignment_id": assignment.id,
            "order_id": assignment.order_id,
            "customer_name": assignment.order.customer.name,
            "phone": assignment.order.customer.phone,
            "building": assignment.order.customer.building,
            "address": assignment.order.customer.address,
            "latitude": assignment.order.customer.latitude,
            "longitude": assignment.order.customer.longitude,
            "route_order": idx,
            "status": assignment.status,
        })

    record_audit_event(
        db,
        store_id=store_id,
        action=AuditAction.route_optimized,
        entity_type="delivery_route",
        entity_id=agent_id or "store",
        evidence={"strategy": strategy, "order_ids": [row.order_id for row in ordered]},
    )
    db.commit()
    return {
        "store_id": store_id,
        "agent_id": agent_id,
        "ordered_order_ids": [row.order_id for row in ordered],
        "stops": stops,
        "strategy": strategy,
    }


def reconcile_upi_payment(db: Session, store_id: int, payload: UpiWebhookIn) -> Payment:
    existing = db.scalar(select(Payment).where(Payment.store_id == store_id, Payment.provider_ref == payload.provider_ref))
    if existing:
        existing.status = PaymentStatus.duplicate
        db.commit()
        db.refresh(existing)
        return existing

    order = None
    customer_id = payload.customer_id
    if payload.order_id:
        order = db.scalar(select(Order).where(Order.id == payload.order_id, Order.store_id == store_id))
        if not order:
            raise ValueError(f"Order {payload.order_id} not found")
        customer_id = order.customer_id

    if customer_id:
        customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.store_id == store_id))
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
    else:
        customer = None

    payment = Payment(
        store_id=store_id,
        customer_id=customer_id,
        order_id=payload.order_id,
        provider_ref=payload.provider_ref,
        amount=payload.amount,
        payer_vpa=payload.payer_vpa,
        raw_payload=json.dumps(payload.raw_payload or {}, sort_keys=True),
        status=PaymentStatus.received,
    )
    db.add(payment)

    if customer:
        applied = min(payload.amount, max(customer.credit_balance, 0.0))
        if applied > 0:
            customer.credit_balance = round(customer.credit_balance - applied, 2)
            db.add(
                LedgerEntry(
                    store_id=store_id,
                    customer_id=customer.id,
                    order_id=payload.order_id,
                    amount=-applied,
                    reason=f"UPI payment reconciled: {payload.provider_ref}",
                )
            )
        payment.status = PaymentStatus.reconciled
        payment.reconciled_at = datetime.now(timezone.utc)

    if order and payload.amount >= order.amount_due:
        order.is_credit = False

    record_audit_event(
        db,
        store_id=store_id,
        action=AuditAction.payment_reconciled,
        entity_type="payment",
        entity_id=payload.provider_ref,
        evidence={"amount": payload.amount, "customer_id": customer_id, "order_id": payload.order_id},
    )
    db.commit()
    db.refresh(payment)
    return payment
