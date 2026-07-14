"""
Pydantic v2 schemas — request/response contracts for every API endpoint.
Kept separate from SQLAlchemy models so the API surface can evolve independently.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.domain import (
    AiUsagePurpose,
    AuditAction,
    DeliveryStatus,
    MessageType,
    OperatorRole,
    OrderStatus,
    OutboundStatus,
    ParseStatus,
    PaymentStatus,
    ProductStatus,
    StaffAssignmentStatus,
)

# ── Shared ─────────────────────────────────────────────────────────────────────

class OrderItemOut(BaseModel):
    id:         int
    name:       str
    quantity:   float
    unit:       str
    confidence: float   # 0–1; shown in UI to flag low-confidence parses
    product_id: int | None = None
    substitution_for_item_id: int | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    store_id: int
    sku: str
    name: str
    canonical_name: str
    category: str | None
    unit: str
    price: float | None
    stock_quantity: float | None
    status: ProductStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductCreateIn(BaseModel):
    sku: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=160)
    canonical_name: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    unit: str = Field(default="pcs", min_length=1, max_length=32)
    price: float | None = Field(default=None, ge=0)
    stock_quantity: float | None = Field(default=None, ge=0)
    status: ProductStatus = ProductStatus.active
    notes: str | None = Field(default=None, max_length=500)


class ProductUpdateIn(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    canonical_name: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    price: float | None = Field(default=None, ge=0)
    stock_quantity: float | None = Field(default=None, ge=0)
    status: ProductStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class ProductSubstitutionIn(BaseModel):
    substitute_product_id: int
    reason: str | None = Field(default=None, max_length=160)


class ProductSubstitutionOut(BaseModel):
    id: int
    store_id: int
    product_id: int
    substitute_product_id: int
    reason: str | None
    created_at: datetime
    substitute: ProductOut | None = None

    model_config = {"from_attributes": True}


class InboundMessageOut(BaseModel):
    id: int
    source: str
    external_message_id: str | None
    message_type: MessageType
    raw_text: str | None
    extracted_text: str | None
    media_type: str | None
    language: str | None
    parse_status: ParseStatus
    parse_failure_reason: str | None
    received_at: datetime

    model_config = {"from_attributes": True}

class CustomerOut(BaseModel):
    id:              int
    name:            str
    phone:           str
    building:        str | None
    address:         str | None = None
    latitude:        float | None = None
    longitude:       float | None = None
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
    message:      InboundMessageOut | None = None

    model_config = {"from_attributes": True}


class CustomerHistoryOut(BaseModel):
    customer: CustomerOut
    recent_orders: list[OrderOut]
    lifetime_orders: int
    lifetime_amount_due: float
    top_items: list[TopItem] = Field(default_factory=list)


class StoreOut(BaseModel):
    id:         int
    name:       str
    slug:       str
    phone:      str | None
    address:    str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreCreateIn(BaseModel):
    name:    str = Field(..., min_length=1, max_length=160)
    slug:    str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    phone:   str | None = None
    address: str | None = None


class OperatorOut(BaseModel):
    id:         int
    store_id:   int
    username:   str
    role:       OperatorRole
    created_at: datetime

    model_config = {"from_attributes": True}


class OperatorCreateIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8, max_length=160)
    role:     OperatorRole = OperatorRole.owner
    store_id: int = 1


class LoginIn(BaseModel):
    username: str
    password: str
    store_id: int = 1


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    operator: OperatorOut


# ── Ingest ─────────────────────────────────────────────────────────────────────

class IngestMessageIn(BaseModel):
    """
    Normalised inbound message payload.
    Provider-specific webhook bodies (Twilio, Meta Cloud API) are mapped
    to this shape in the webhook route before hitting the ingestion service.
    """
    phone:         str          = Field(..., examples=["+919999999999"])
    store_id:      int | None   = None
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


class OrderItemCorrectionIn(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1, max_length=160)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = Field(default="pcs", min_length=1, max_length=32)
    confidence: float = Field(default=1.0, ge=0, le=1)
    product_id: int | None = None
    substitution_for_item_id: int | None = None
    notes: str | None = Field(default=None, max_length=300)


class OrderReviewResolveIn(BaseModel):
    items: list[OrderItemCorrectionIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)
    status: OrderStatus = OrderStatus.pending


class OrderCorrectionIn(BaseModel):
    items: list[OrderItemCorrectionIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)


class AmountUpdateIn(BaseModel):
    amount_due: float = Field(..., ge=0)
    is_credit:  bool  = False


class OrderNotesUpdateIn(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class RepeatOrderIn(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    status: OrderStatus = OrderStatus.pending


class StaffAssignmentIn(BaseModel):
    operator_id: int
    role: str = Field(default="fulfillment", max_length=40)
    notes: str | None = Field(default=None, max_length=500)


class StaffAssignmentUpdateIn(BaseModel):
    status: StaffAssignmentStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class StaffAssignmentOut(BaseModel):
    id: int
    store_id: int
    order_id: int
    operator_id: int
    role: str
    status: StaffAssignmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Customer mutations ─────────────────────────────────────────────────────────

class CustomerUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    building: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    language_hint: str | None = None


class CustomerCreateIn(BaseModel):
    name:          str         = Field(..., min_length=1, max_length=120)
    phone:         str         = Field(..., examples=["+919999999999"])
    store_id:      int | None  = None
    building:      str | None  = None
    address:       str | None  = None
    latitude:      float | None = Field(default=None, ge=-90, le=90)
    longitude:     float | None = Field(default=None, ge=-180, le=180)
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


class DailyClosingOut(BaseModel):
    store_id: int
    day: str
    orders_created: int
    delivered: int
    cancelled: int
    needs_review: int
    amount_due_total: float
    credit_extended_total: float
    pending_end_of_day: int = 0
    packed_end_of_day: int = 0
    manual_intervention_rate: float = 0.0


class OperationsDailyReportOut(BaseModel):
    store_id: int
    day: str
    orders_created: int
    orders_delivered: int
    orders_cancelled: int
    needs_review: int
    pending: int
    packed: int
    amount_due_total: float
    credit_extended_total: float
    average_order_value: float
    manual_intervention_rate: float
    top_items: list[TopItem]
    ai_usage_count: int
    ai_estimated_cost: float


class FeatureFlagsOut(BaseModel):
    catalog_enabled: bool
    staff_assignment_enabled: bool
    repeat_orders_enabled: bool
    ai_usage_tracking_enabled: bool
    payments_enabled: bool
    delivery_enabled: bool



# ── Ledger ─────────────────────────────────────────────────────────────────────

class LedgerEntryOut(BaseModel):
    id:         int
    amount:     float
    reason:     str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Outbound / delivery / payment operations ─────────────────────────────────

class OutboundMessageOut(BaseModel):
    id:                  int
    store_id:            int
    order_id:            int | None
    customer_id:         int
    destination_phone:   str
    body:                str
    provider:            str
    provider_message_id: str | None
    failure_reason:      str | None = None
    dispatch_attempts:   int
    status:              OutboundStatus
    created_at:          datetime
    sent_at:             datetime | None

    model_config = {"from_attributes": True}


class OutboundConfirmationIn(BaseModel):
    body: str | None = Field(default=None, max_length=500)


class DeliveryAgentCreateIn(BaseModel):
    name:  str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=6, max_length=32)
    active: bool = True


class DeliveryAgentOut(BaseModel):
    id:         int
    store_id:   int
    name:       str
    phone:      str
    active:     bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryAssignmentIn(BaseModel):
    agent_id: int
    route_order: int = Field(default=0, ge=0)
    notes: str | None = None


class DeliveryAssignmentStatusIn(BaseModel):
    status: DeliveryStatus


class DeliveryAssignmentOut(BaseModel):
    id:          int
    store_id:    int
    order_id:    int
    agent_id:    int
    route_order: int
    status:      DeliveryStatus
    notes:       str | None
    assigned_at: datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


class RouteStop(BaseModel):
    assignment_id: int
    order_id: int
    customer_name: str
    phone: str
    building: str | None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    route_order: int
    status: DeliveryStatus


class RouteOptimizeIn(BaseModel):
    agent_id: int | None = None
    order_ids: list[int] | None = None
    start_latitude: float | None = Field(default=None, ge=-90, le=90)
    start_longitude: float | None = Field(default=None, ge=-180, le=180)


class RouteOptimizeOut(BaseModel):
    store_id: int
    agent_id: int | None
    ordered_order_ids: list[int]
    stops: list[RouteStop]
    strategy: str


class UpiWebhookIn(BaseModel):
    provider_ref: str = Field(..., min_length=3, max_length=160)
    amount: float = Field(..., gt=0)
    payer_vpa: str | None = None
    customer_id: int | None = None
    order_id: int | None = None
    raw_payload: dict | None = None


class PaymentOut(BaseModel):
    id:            int
    store_id:      int
    customer_id:   int | None
    order_id:      int | None
    provider:      str
    provider_ref:  str
    amount:        float
    payer_vpa:     str | None
    status:        PaymentStatus
    received_at:   datetime
    reconciled_at: datetime | None

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


class AiUsageEventCreateIn(BaseModel):
    provider: str = Field(..., min_length=1, max_length=40)
    model: str | None = Field(default=None, max_length=120)
    purpose: AiUsagePurpose
    inbound_message_id: int | None = None
    order_id: int | None = None
    estimated_units: float = Field(default=0.0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0)
    success: bool = True
    failure_reason: str | None = Field(default=None, max_length=160)


class AiUsageEventOut(BaseModel):
    id: int
    store_id: int
    provider: str
    model: str | None
    purpose: AiUsagePurpose
    inbound_message_id: int | None
    order_id: int | None
    estimated_units: float
    estimated_cost: float
    success: bool
    failure_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiUsageSummaryOut(BaseModel):
    store_id: int
    day: str | None = None
    total_events: int
    total_estimated_units: float
    total_estimated_cost: float
    by_provider: dict[str, int]
    by_purpose: dict[str, int]


class AuditEventOut(BaseModel):
    id: int
    store_id: int
    actor_type: str
    actor_id: str | None
    action: AuditAction
    entity_type: str
    entity_id: str
    evidence: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
