"""
Pydantic v2 schemas — request/response contracts for every API endpoint.
Kept separate from SQLAlchemy models so the API surface can evolve independently.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.domain import MessageType, OrderStatus


# ── Shared ─────────────────────────────────────────────────────────────────────

class OrderItemOut(BaseModel):
    id:         int
    name:       str
    quantity:   float
    unit:       str
    confidence: float   # 0–1; shown in UI to flag low-confidence parses

    model_config = {"from_attributes": True}


class CustomerOut(BaseModel):
    id:              int
    name:            str
    phone:           str
    building:        str | None
    language_hint:   str | None
    credit_balance:  float
    last_order_at:   datetime | None
    dormant:         bool = False   # computed, not stored

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id:           int
    status:       OrderStatus
    amount_due:   float
    is_credit:    bool
    notes:        str | None
    created_at:   datetime
    updated_at:   datetime
    delivered_at: datetime | None
    customer:     CustomerOut
    items:        list[OrderItemOut]

    model_config = {"from_attributes": True}


# ── Ingest ─────────────────────────────────────────────────────────────────────

class IngestMessageIn(BaseModel):
    """
    Normalised inbound message payload.
    Provider-specific webhook bodies (Twilio, Meta Cloud API) are mapped
    to this shape in the webhook route before hitting the ingestion service.
    """
    phone:         str          = Field(..., examples=["+919999999999"])
    customer_name: str | None   = None
    building:      str | None   = None
    message_type:  MessageType  = MessageType.text
    text:          str | None   = None
    media_url:     str | None   = None
    media_type:    str | None   = None
    source:        str          = "manual"
    external_message_id: str | None = None
    language:      str | None   = None

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, v: str) -> str:
        # Strip spaces and dashes; keep + prefix
        return v.replace(" ", "").replace("-", "")


# ── Order mutations ────────────────────────────────────────────────────────────

class StatusUpdateIn(BaseModel):
    status: OrderStatus


class AmountUpdateIn(BaseModel):
    amount_due: float = Field(..., ge=0)
    is_credit:  bool  = False


# ── Customer mutations ─────────────────────────────────────────────────────────

class CustomerCreateIn(BaseModel):
    name:          str         = Field(..., min_length=1, max_length=120)
    phone:         str         = Field(..., examples=["+919999999999"])
    building:      str | None  = None
    language_hint: str | None  = None

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, v: str) -> str:
        return v.replace(" ", "").replace("-", "")


class CreditAdjustIn(BaseModel):
    """
    Positive amount = extend credit (udhaari).
    Negative amount = record payment received.
    """
    amount: float = Field(..., description="Positive to extend credit, negative to record payment")
    reason: str   = Field(default="Manual adjustment", max_length=200)


# ── Dashboard ──────────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    pending:          int
    packed:           int
    delivered_today:  int
    needs_review:     int
    dormant_customers: int
    total_credit:     float


# ── Ledger ─────────────────────────────────────────────────────────────────────

class LedgerEntryOut(BaseModel):
    id:         int
    amount:     float
    reason:     str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analytics ──────────────────────────────────────────────────────────────────

class DailyMetric(BaseModel):
    day:     str
    orders:  int
    revenue: float


class TopItem(BaseModel):
    name:  str
    count: int
    total_quantity: float


class InputMethodStat(BaseModel):
    message_type: str
    count:        int
