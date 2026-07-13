"""
Domain models — SQLAlchemy 2.x mapped_column style.

Key synthesis decisions vs previous iterations:
  - OrderItem is a first-class table (not a JSON blob), enabling item-level analytics.
  - confidence per item surfaces parsing uncertainty without blocking the whole order.
  - needs_review is a real OrderStatus value, not a boolean flag.
  - LedgerEntry records every credit movement for a full audit trail.
  - Customer.credit_balance is the running sum; LedgerEntry is the history.
"""

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(StrEnum):
    pending      = "pending"
    packed       = "packed"
    delivered    = "delivered"
    cancelled    = "cancelled"
    needs_review = "needs_review"   # image/voice with no parseable text yet


class MessageType(StrEnum):
    text  = "text"
    image = "image"
    voice = "voice"
    manual = "manual"


class ParseStatus(StrEnum):
    pending      = "pending"
    parsed       = "parsed"
    needs_review = "needs_review"
    failed       = "failed"


class OperatorRole(StrEnum):
    owner   = "owner"
    manager = "manager"
    staff   = "staff"


class OutboundStatus(StrEnum):
    queued    = "queued"
    sent      = "sent"
    simulated = "simulated"
    failed    = "failed"


class DeliveryStatus(StrEnum):
    assigned  = "assigned"
    picked_up = "picked_up"
    delivered = "delivered"
    failed    = "failed"


class PaymentStatus(StrEnum):
    received   = "received"
    reconciled = "reconciled"
    duplicate  = "duplicate"
    failed     = "failed"


class AuditAction(StrEnum):
    order_status_updated = "order_status_updated"
    order_amount_updated = "order_amount_updated"
    credit_adjusted = "credit_adjusted"
    outbound_confirmation_created = "outbound_confirmation_created"
    delivery_assigned = "delivery_assigned"
    delivery_status_updated = "delivery_status_updated"
    route_optimized = "route_optimized"
    payment_reconciled = "payment_reconciled"
    duplicate_message_ignored = "duplicate_message_ignored"
    order_review_resolved = "order_review_resolved"
    order_items_corrected = "order_items_corrected"
    customer_updated = "customer_updated"


# ── Store / tenancy ───────────────────────────────────────────────────────────

class Store(Base):
    __tablename__ = "stores"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    name:       Mapped[str]      = mapped_column(String(160), default="Main Store")
    slug:       Mapped[str]      = mapped_column(String(80), unique=True, index=True)
    phone:      Mapped[str | None] = mapped_column(String(32), nullable=True)
    address:    Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customers: Mapped[list["Customer"]] = relationship(back_populates="store")
    operators: Mapped[list["Operator"]] = relationship(back_populates="store")


class Operator(Base):
    __tablename__ = "operators"
    __table_args__ = (UniqueConstraint("store_id", "username", name="uq_operator_store_username"),)

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True)
    store_id:      Mapped[int]          = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    username:      Mapped[str]          = mapped_column(String(80), index=True)
    password_hash: Mapped[str]          = mapped_column(String(240))
    role:          Mapped[OperatorRole] = mapped_column(Enum(OperatorRole), default=OperatorRole.owner)
    created_at:    Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)

    store: Mapped[Store] = relationship(back_populates="operators")


# ── Customer ──────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("store_id", "phone", name="uq_customer_store_phone"),)

    id:              Mapped[int]            = mapped_column(Integer, primary_key=True)
    store_id:        Mapped[int]            = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    name:            Mapped[str]            = mapped_column(String(120), default="Unknown customer")
    phone:           Mapped[str]            = mapped_column(String(32), index=True)
    building:        Mapped[str | None]     = mapped_column(String(120), nullable=True)
    address:         Mapped[str | None]     = mapped_column(Text, nullable=True)
    latitude:        Mapped[float | None]   = mapped_column(Float, nullable=True)
    longitude:       Mapped[float | None]   = mapped_column(Float, nullable=True)
    language_hint:   Mapped[str | None]     = mapped_column(String(40), nullable=True)
    credit_balance:  Mapped[float]          = mapped_column(Float, default=0.0)
    last_order_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)

    store:    Mapped[Store]                 = relationship(back_populates="customers")
    orders:   Mapped[list["Order"]]          = relationship(back_populates="customer")
    messages: Mapped[list["InboundMessage"]] = relationship(back_populates="customer")
    ledger:   Mapped[list["LedgerEntry"]]    = relationship(back_populates="customer")


# ── InboundMessage ────────────────────────────────────────────────────────────

class InboundMessage(Base):
    """Raw WhatsApp message as received from the provider webhook."""
    __tablename__ = "inbound_messages"
    __table_args__ = (UniqueConstraint("store_id", "source", "external_message_id", name="uq_inbound_store_source_external"),)

    id:           Mapped[int]         = mapped_column(Integer, primary_key=True)
    store_id:     Mapped[int]         = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    customer_id:  Mapped[int]         = mapped_column(ForeignKey("customers.id"), index=True)
    source:       Mapped[str]         = mapped_column(String(40), default="manual", index=True)
    external_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType))
    raw_text:     Mapped[str | None]  = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url:    Mapped[str | None]  = mapped_column(Text, nullable=True)
    media_type:   Mapped[str | None]  = mapped_column(String(120), nullable=True)
    language:     Mapped[str | None]  = mapped_column(String(40), nullable=True)
    parse_status: Mapped[ParseStatus] = mapped_column(Enum(ParseStatus), default=ParseStatus.pending)
    parse_failure_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    received_at:  Mapped[datetime]    = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped[Customer]       = relationship(back_populates="messages")
    order:    Mapped["Order | None"] = relationship(back_populates="message")


# ── Order ─────────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
    store_id:     Mapped[int]              = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    customer_id:  Mapped[int]              = mapped_column(ForeignKey("customers.id"), index=True)
    message_id:   Mapped[int | None]       = mapped_column(ForeignKey("inbound_messages.id"), nullable=True)
    status:       Mapped[OrderStatus]      = mapped_column(Enum(OrderStatus), default=OrderStatus.pending, index=True)
    notes:        Mapped[str | None]       = mapped_column(Text, nullable=True)
    amount_due:   Mapped[float]            = mapped_column(Float, default=0.0)
    is_credit:    Mapped[bool]             = mapped_column(Integer, default=False)  # udhaari flag
    created_at:   Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at:   Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    delivered_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer]              = relationship(back_populates="orders")
    message:  Mapped[InboundMessage | None] = relationship(back_populates="order")
    items:    Mapped[list["OrderItem"]]     = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    delivery_assignment: Mapped["DeliveryAssignment | None"] = relationship(back_populates="order")
    outbound_messages: Mapped[list["OutboundMessage"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


# ── OrderItem ─────────────────────────────────────────────────────────────────

class OrderItem(Base):
    """
    One line item within an order.
    Storing items normalised (not as JSON) enables per-item analytics:
    top items, total kg of atta this week, etc.
    confidence reflects parser certainty — low confidence items surface in the UI.
    """
    __tablename__ = "order_items"

    id:         Mapped[int]   = mapped_column(Integer, primary_key=True)
    order_id:   Mapped[int]   = mapped_column(ForeignKey("orders.id"), index=True)
    name:       Mapped[str]   = mapped_column(String(160))
    quantity:   Mapped[float] = mapped_column(Float, default=1.0)
    unit:       Mapped[str]   = mapped_column(String(32), default="pcs")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)

    order: Mapped[Order] = relationship(back_populates="items")


# ── LedgerEntry ───────────────────────────────────────────────────────────────

class LedgerEntry(Base):
    """
    Immutable audit log of every credit/debit against a customer's udhaari balance.
    Positive amount = credit extended to customer (they owe us).
    Negative amount = payment received from customer.
    """
    __tablename__ = "ledger_entries"

    id:          Mapped[int]   = mapped_column(Integer, primary_key=True)
    store_id:    Mapped[int]   = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    customer_id: Mapped[int]   = mapped_column(ForeignKey("customers.id"), index=True)
    order_id:    Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    amount:      Mapped[float] = mapped_column(Float)   # positive = owed, negative = paid
    reason:      Mapped[str]   = mapped_column(String(200))
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped[Customer] = relationship(back_populates="ledger")


# ── Outbound confirmations ───────────────────────────────────────────────────

class OutboundMessage(Base):
    __tablename__ = "outbound_messages"

    id:                  Mapped[int]            = mapped_column(Integer, primary_key=True)
    store_id:            Mapped[int]            = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    order_id:            Mapped[int | None]     = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    customer_id:         Mapped[int]            = mapped_column(ForeignKey("customers.id"), index=True)
    destination_phone:   Mapped[str]            = mapped_column(String(32))
    body:                Mapped[str]            = mapped_column(Text)
    provider:            Mapped[str]            = mapped_column(String(40), default="simulation")
    provider_message_id: Mapped[str | None]     = mapped_column(String(140), nullable=True)
    failure_reason:      Mapped[str | None]     = mapped_column(Text, nullable=True)
    dispatch_attempts:   Mapped[int]            = mapped_column(Integer, default=0)
    status:              Mapped[OutboundStatus] = mapped_column(Enum(OutboundStatus), default=OutboundStatus.queued)
    created_at:          Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at:             Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="outbound_messages")
    customer: Mapped[Customer] = relationship()


# ── Delivery assignment ───────────────────────────────────────────────────────

class DeliveryAgent(Base):
    __tablename__ = "delivery_agents"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    store_id:   Mapped[int]      = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    name:       Mapped[str]      = mapped_column(String(120))
    phone:      Mapped[str]      = mapped_column(String(32), index=True)
    active:     Mapped[bool]     = mapped_column(Integer, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True)
    store_id:    Mapped[int]            = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    order_id:    Mapped[int]            = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    agent_id:    Mapped[int]            = mapped_column(ForeignKey("delivery_agents.id"), index=True)
    route_order: Mapped[int]            = mapped_column(Integer, default=0)
    status:      Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.assigned)
    notes:       Mapped[str | None]     = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped[Order] = relationship(back_populates="delivery_assignment")
    agent: Mapped[DeliveryAgent] = relationship()


# ── UPI payment reconciliation ────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("store_id", "provider_ref", name="uq_payment_store_provider_ref"),)

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True)
    store_id:       Mapped[int]           = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    customer_id:    Mapped[int | None]    = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    order_id:       Mapped[int | None]    = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    provider:       Mapped[str]           = mapped_column(String(40), default="upi")
    provider_ref:   Mapped[str]           = mapped_column(String(160), index=True)
    amount:         Mapped[float]         = mapped_column(Float)
    payer_vpa:      Mapped[str | None]    = mapped_column(String(160), nullable=True)
    status:         Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.received)
    raw_payload:    Mapped[str | None]    = mapped_column(Text, nullable=True)
    received_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    reconciled_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer | None] = relationship()
    order: Mapped[Order | None] = relationship(back_populates="payments")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id:          Mapped[int]         = mapped_column(Integer, primary_key=True)
    store_id:    Mapped[int]         = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    actor_type:  Mapped[str]         = mapped_column(String(40), default="system")
    actor_id:    Mapped[str | None]  = mapped_column(String(120), nullable=True)
    action:      Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    entity_type: Mapped[str]         = mapped_column(String(80), index=True)
    entity_id:   Mapped[str]         = mapped_column(String(120), index=True)
    evidence:    Mapped[str | None]  = mapped_column(Text, nullable=True)
    created_at:  Mapped[datetime]    = mapped_column(DateTime(timezone=True), default=utcnow)
