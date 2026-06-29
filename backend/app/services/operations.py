import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import (
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
    db.add(outbound)
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
            "route_order": row.route_order,
            "status": row.status,
        }
        for row in rows
    ]


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

    db.commit()
    db.refresh(payment)
    return payment
