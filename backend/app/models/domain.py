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
    partially_refunded = "partially_refunded"
    refunded = "refunded"
    duplicate  = "duplicate"
    failed     = "failed"


class PaymentMethod(StrEnum):
    cash = "cash"
    upi = "upi"
    split = "split"


class RefundStatus(StrEnum):
    requested = "requested"
    approved = "approved"
    rejected = "rejected"


class SettlementStatus(StrEnum):
    draft = "draft"
    closed = "closed"


class ProductStatus(StrEnum):
    active = "active"
    inactive = "inactive"


class StaffAssignmentStatus(StrEnum):
    assigned = "assigned"
    accepted = "accepted"
    completed = "completed"
    reassigned = "reassigned"
    cancelled = "cancelled"


class AiUsagePurpose(StrEnum):
    parse = "parse"
    ocr = "ocr"
    stt = "stt"
    review_assist = "review_assist"


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
    product_created = "product_created"
    product_updated = "product_updated"
    product_substitution_added = "product_substitution_added"
    staff_assignment_created = "staff_assignment_created"
    staff_assignment_updated = "staff_assignment_updated"
    order_note_updated = "order_note_updated"
    repeat_order_created = "repeat_order_created"
    ai_usage_recorded = "ai_usage_recorded"
    payment_recorded = "payment_recorded"
    refund_requested = "refund_requested"
    refund_approved = "refund_approved"
    refund_rejected = "refund_rejected"
    order_cancelled_financially = "order_cancelled_financially"
    settlement_generated = "settlement_generated"
    settlement_closed = "settlement_closed"
    accounting_export_generated = "accounting_export_generated"


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
    products: Mapped[list["Product"]] = relationship(back_populates="store")


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
    staff_assignments: Mapped[list["StaffAssignment"]] = relationship(back_populates="order")


# ── Product catalog ──────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("store_id", "sku", name="uq_product_store_sku"),)

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True)
    store_id:       Mapped[int]           = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    sku:            Mapped[str]           = mapped_column(String(80), index=True)
    name:           Mapped[str]           = mapped_column(String(160), index=True)
    canonical_name: Mapped[str]           = mapped_column(String(160), index=True)
    category:       Mapped[str | None]    = mapped_column(String(80), nullable=True, index=True)
    unit:           Mapped[str]           = mapped_column(String(32), default="pcs")
    price:          Mapped[float | None]  = mapped_column(Float, nullable=True)
    stock_quantity: Mapped[float | None]  = mapped_column(Float, nullable=True)
    status:         Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.active, index=True)
    notes:          Mapped[str | None]    = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    store: Mapped[Store] = relationship(back_populates="products")
    substitutions_from: Mapped[list["ProductSubstitution"]] = relationship(
        back_populates="product", foreign_keys="ProductSubstitution.product_id", cascade="all, delete-orphan"
    )


class ProductSubstitution(Base):
    __tablename__ = "product_substitutions"
    __table_args__ = (UniqueConstraint("store_id", "product_id", "substitute_product_id", name="uq_product_substitution_pair"),)

    id:                    Mapped[int]      = mapped_column(Integer, primary_key=True)
    store_id:              Mapped[int]      = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    product_id:            Mapped[int]      = mapped_column(ForeignKey("products.id"), index=True)
    substitute_product_id: Mapped[int]      = mapped_column(ForeignKey("products.id"), index=True)
    reason:                Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at:            Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped[Product] = relationship(foreign_keys=[product_id], back_populates="substitutions_from")
    substitute: Mapped[Product] = relationship(foreign_keys=[substitute_product_id])


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
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    substitution_for_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="items", foreign_keys=[order_id])
    product: Mapped[Product | None] = relationship()


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"

    id:          Mapped[int]                   = mapped_column(Integer, primary_key=True)
    store_id:    Mapped[int]                   = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    order_id:    Mapped[int]                   = mapped_column(ForeignKey("orders.id"), index=True)
    operator_id: Mapped[int]                   = mapped_column(ForeignKey("operators.id"), index=True)
    role:        Mapped[str]                   = mapped_column(String(40), default="fulfillment")
    status:      Mapped[StaffAssignmentStatus] = mapped_column(Enum(StaffAssignmentStatus), default=StaffAssignmentStatus.assigned, index=True)
    notes:       Mapped[str | None]            = mapped_column(Text, nullable=True)
    created_at:  Mapped[datetime]              = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime]              = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped[Order] = relationship(back_populates="staff_assignments")
    operator: Mapped[Operator] = relationship()


class AiUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id:                 Mapped[int]            = mapped_column(Integer, primary_key=True)
    store_id:           Mapped[int]            = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    provider:           Mapped[str]            = mapped_column(String(40), index=True)
    model:              Mapped[str | None]     = mapped_column(String(120), nullable=True)
    purpose:            Mapped[AiUsagePurpose] = mapped_column(Enum(AiUsagePurpose), index=True)
    inbound_message_id: Mapped[int | None]     = mapped_column(ForeignKey("inbound_messages.id"), nullable=True, index=True)
    order_id:           Mapped[int | None]     = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    estimated_units:    Mapped[float]          = mapped_column(Float, default=0.0)
    estimated_cost:     Mapped[float]          = mapped_column(Float, default=0.0)
    success:            Mapped[bool]           = mapped_column(Integer, default=True)
    failure_reason:     Mapped[str | None]     = mapped_column(String(160), nullable=True)
    created_at:         Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


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
    method:         Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.upi, index=True)
    cash_amount:    Mapped[float]         = mapped_column(Float, default=0.0)
    upi_amount:     Mapped[float]         = mapped_column(Float, default=0.0)
    refunded_amount: Mapped[float]        = mapped_column(Float, default=0.0)
    notes:          Mapped[str | None]    = mapped_column(Text, nullable=True)
    received_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    reconciled_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer | None] = relationship()
    order: Mapped[Order | None] = relationship(back_populates="payments")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment")


class Refund(Base):
    __tablename__ = "refunds"

    id:          Mapped[int]          = mapped_column(Integer, primary_key=True)
    store_id:    Mapped[int]          = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    payment_id:  Mapped[int]          = mapped_column(ForeignKey("payments.id"), index=True)
    order_id:    Mapped[int | None]   = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    amount:      Mapped[float]        = mapped_column(Float)
    reason:      Mapped[str]          = mapped_column(String(240))
    status:      Mapped[RefundStatus] = mapped_column(Enum(RefundStatus), default=RefundStatus.requested, index=True)
    requested_by: Mapped[str | None]  = mapped_column(String(120), nullable=True)
    decided_by:  Mapped[str | None]   = mapped_column(String(120), nullable=True)
    requested_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment: Mapped[Payment] = relationship(back_populates="refunds")


class DailySettlement(Base):
    __tablename__ = "daily_settlements"
    __table_args__ = (UniqueConstraint("store_id", "business_day", name="uq_settlement_store_day"),)

    id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
    store_id:     Mapped[int]              = mapped_column(ForeignKey("stores.id"), default=1, index=True)
    business_day: Mapped[str]              = mapped_column(String(10), index=True)
    cash_total:   Mapped[float]            = mapped_column(Float, default=0.0)
    upi_total:    Mapped[float]            = mapped_column(Float, default=0.0)
    refund_total: Mapped[float]            = mapped_column(Float, default=0.0)
    net_total:    Mapped[float]            = mapped_column(Float, default=0.0)
    payment_count: Mapped[int]             = mapped_column(Integer, default=0)
    status:       Mapped[SettlementStatus] = mapped_column(Enum(SettlementStatus), default=SettlementStatus.draft, index=True)
    notes:        Mapped[str | None]       = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at:    Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by:    Mapped[str | None]       = mapped_column(String(120), nullable=True)


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
