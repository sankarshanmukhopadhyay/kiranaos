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
    DateTime, Enum, Float, ForeignKey, Integer, String, Text,
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


# ── Customer ──────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id:              Mapped[int]            = mapped_column(Integer, primary_key=True)
    name:            Mapped[str]            = mapped_column(String(120), default="Unknown customer")
    phone:           Mapped[str]            = mapped_column(String(32), unique=True, index=True)
    building:        Mapped[str | None]     = mapped_column(String(120), nullable=True)
    language_hint:   Mapped[str | None]     = mapped_column(String(40), nullable=True)
    credit_balance:  Mapped[float]          = mapped_column(Float, default=0.0)
    last_order_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)

    orders:   Mapped[list["Order"]]          = relationship(back_populates="customer")
    messages: Mapped[list["InboundMessage"]] = relationship(back_populates="customer")
    ledger:   Mapped[list["LedgerEntry"]]    = relationship(back_populates="customer")


# ── InboundMessage ────────────────────────────────────────────────────────────

class InboundMessage(Base):
    """Raw WhatsApp message as received from the provider webhook."""
    __tablename__ = "inbound_messages"

    id:           Mapped[int]         = mapped_column(Integer, primary_key=True)
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
    received_at:  Mapped[datetime]    = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped[Customer]       = relationship(back_populates="messages")
    order:    Mapped["Order | None"] = relationship(back_populates="message")


# ── Order ─────────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
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
    customer_id: Mapped[int]   = mapped_column(ForeignKey("customers.id"), index=True)
    order_id:    Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    amount:      Mapped[float] = mapped_column(Float)   # positive = owed, negative = paid
    reason:      Mapped[str]   = mapped_column(String(200))
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped[Customer] = relationship(back_populates="ledger")
