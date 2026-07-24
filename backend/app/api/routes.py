"""
routes.py — All API endpoints.

Route organisation:
  /health                      — liveness probe
  /dashboard/summary           — single-call dashboard load
  /ingest/messages             — normalised inbound message (from webhook or direct)
  /webhooks/whatsapp           — GET (Meta verification) + POST (Twilio/Meta inbound)
  /orders                      — list, detail, status update, amount update
  /customers                   — list, create, detail, credit adjust, ledger
  /analytics/*                 — daily metrics, top items, input methods
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.domain import AuditAction, MessageType, Operator, OperatorRole, OrderStatus, Store
from app.schemas.domain import (
    AiUsageEventCreateIn,
    AiUsageEventOut,
    AiUsageSummaryOut,
    AmountUpdateIn,
    AuditEventOut,
    CreditAdjustIn,
    CustomerCreateIn,
    CustomerOut,
    CustomerUpdateIn,
    DailyClosingOut,
    DailyMetric,
    DashboardSummary,
    DeliveryAgentCreateIn,
    DeliveryAgentOut,
    DeliveryAssignmentIn,
    DeliveryAssignmentOut,
    DeliveryAssignmentStatusIn,
    FeatureFlagsOut,
    IngestMessageIn,
    InputMethodStat,
    LedgerEntryOut,
    LoginIn,
    OperationsDailyReportOut,
    OperatorCreateIn,
    OperatorOut,
    OrderCorrectionIn,
    OrderNotesUpdateIn,
    OrderOut,
    OrderReviewResolveIn,
    OutboundConfirmationIn,
    OutboundMessageOut,
    ManualPaymentIn,
    OrderPaymentSummaryOut,
    PaymentOut,
    RefundDecisionIn,
    RefundOut,
    RefundRequestIn,
    SettlementCloseIn,
    SettlementGenerateIn,
    SettlementOut,
    ProductCreateIn,
    ProductOut,
    ProductStatus,
    ProductSubstitutionIn,
    ProductSubstitutionOut,
    ProductUpdateIn,
    RepeatOrderIn,
    RouteOptimizeIn,
    RouteOptimizeOut,
    RouteStop,
    StaffAssignmentIn,
    StaffAssignmentOut,
    StaffAssignmentUpdateIn,
    StatusUpdateIn,
    StoreCreateIn,
    StoreOut,
    TokenOut,
    TopItem,
    UpiWebhookIn,
)
from app.services.adapters import validate_twilio_signature
from app.services.audit import list_audit_events
from app.services.auth import (
    authenticate_operator,
    create_access_token,
    create_operator,
    current_store_id,
    decode_access_token,
    ensure_default_store,
    operator_count,
    require_roles,
)
from app.services.finance import (
    cancel_order_financially,
    close_settlement,
    decide_refund,
    export_accounting,
    generate_settlement,
    list_settlements,
    order_payment_summary,
    record_manual_payment,
    request_refund,
)
from app.services.ingestion import (
    _is_dormant,
    add_product_substitution,
    adjust_credit,
    ai_usage_events,
    ai_usage_summary,
    assign_staff,
    correct_order_items,
    create_customer,
    create_product,
    customer_history,
    daily_closing,
    daily_metrics,
    dashboard_summary,
    get_customer_with_dormant,
    get_ledger,
    get_order,
    get_product,
    ingest_message,
    input_method_stats,
    list_customers,
    list_orders,
    list_product_substitutions,
    list_products,
    list_staff_assignments,
    operations_daily_report,
    record_ai_usage,
    repeat_order,
    resolve_order_review,
    top_items,
    update_customer,
    update_order_amount,
    update_order_notes,
    update_order_status,
    update_product,
    update_staff_assignment,
)
from app.services.operations import (
    assign_delivery,
    create_delivery_agent,
    create_outbound_confirmation,
    list_delivery_agents,
    optimize_route,
    reconcile_upi_payment,
    route_for_agent,
    update_delivery_status,
)
from app.services.security import verify_upi_webhook_signature

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
StoreDep = Annotated[int, Depends(current_store_id)]
OwnerDep = Annotated[object, Depends(require_roles(OperatorRole.owner))]
ManagerDep = Annotated[object, Depends(require_roles(OperatorRole.owner, OperatorRole.manager))]
StaffDep = Annotated[object, Depends(require_roles(OperatorRole.owner, OperatorRole.manager, OperatorRole.staff))]


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "demo_mode": settings.demo_mode,
        "auth_required": settings.auth_required,
        "providers": {"stt": settings.stt_provider, "ocr": settings.ocr_provider, "parser_ai": settings.parser_ai_provider},
        "feature_flags": {
            "catalog_enabled": settings.catalog_enabled,
            "staff_assignment_enabled": settings.staff_assignment_enabled,
            "repeat_orders_enabled": settings.repeat_orders_enabled,
            "ai_usage_tracking_enabled": settings.ai_usage_tracking_enabled,
            "payments_enabled": settings.payments_enabled,
            "delivery_enabled": settings.delivery_enabled,
        },
    }


@router.get("/features", response_model=FeatureFlagsOut)
def feature_flags():
    settings = get_settings()
    return {
        "catalog_enabled": settings.catalog_enabled,
        "staff_assignment_enabled": settings.staff_assignment_enabled,
        "repeat_orders_enabled": settings.repeat_orders_enabled,
        "ai_usage_tracking_enabled": settings.ai_usage_tracking_enabled,
        "payments_enabled": settings.payments_enabled,
        "delivery_enabled": settings.delivery_enabled,
    }


# ── Stores / operators ────────────────────────────────────────────────────────

@router.post("/stores", response_model=StoreOut, status_code=201)
def create_store(payload: StoreCreateIn, db: DbDep, _operator: OwnerDep):
    existing = db.query(Store).filter(Store.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Store slug already exists")
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/stores/current", response_model=StoreOut)
def current_store(db: DbDep, store_id: StoreDep):
    store = db.get(Store, store_id) or ensure_default_store(db)
    return store


@router.post("/operators", response_model=OperatorOut, status_code=201)
def register_operator(
    payload: OperatorCreateIn,
    db: DbDep,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    settings = get_settings()
    operator = None
    if settings.auth_required and operator_count(db) > 0:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Operator registration requires owner authentication")
        claims = decode_access_token(authorization.split(" ", 1)[1])
        operator = db.get(Operator, int(claims["sub"]))
        if not operator or operator.role != OperatorRole.owner:
            raise HTTPException(status_code=403, detail="Operator registration requires owner role")
        if payload.store_id != operator.store_id:
            raise HTTPException(status_code=403, detail="Cannot create operators outside current store")
    try:
        return create_operator(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: DbDep):
    operator = authenticate_operator(db, payload.username, payload.password, payload.store_id)
    return TokenOut(access_token=create_access_token(operator), operator=OperatorOut.model_validate(operator))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/summary", response_model=DashboardSummary)
def summary(db: DbDep, store_id: StoreDep):
    return dashboard_summary(db, store_id=store_id)


@router.get("/dashboard/daily-closing", response_model=DailyClosingOut)
def closing_summary(db: DbDep, store_id: StoreDep, day: str | None = Query(default=None)):
    return daily_closing(db, store_id=store_id, day=day)


# ── Ingestion ──────────────────────────────────────────────────────────────────

@router.post("/ingest/messages", response_model=OrderOut, status_code=201)
async def ingest(payload: IngestMessageIn, db: DbDep, store_id: StoreDep):
    """
    Normalised ingest endpoint. All provider adapters (Twilio, Meta) map their
    payloads to IngestMessageIn before calling this.
    """
    return await ingest_message(db, payload.model_copy(update={"store_id": store_id}))


# ── WhatsApp Webhooks ──────────────────────────────────────────────────────────

@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    hub_mode:         str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge:    str | None = Query(default=None, alias="hub.challenge"),
):
    """Meta Cloud API webhook verification handshake."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge or "0")
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/webhooks/whatsapp", status_code=200)
async def receive_whatsapp_webhook(db: DbDep):
    """
    Provider webhook entry point. Map the raw provider payload to IngestMessageIn
    here before passing to ingest_message. Twilio has a concrete route at
    /webhooks/twilio/whatsapp; keep this route for future Meta payload mapping.
    """
    return {"status": "accepted"}


@router.post("/webhooks/twilio/whatsapp")
async def receive_twilio_whatsapp(
    request: Request,
    db: DbDep,
    From: str = Form(...),
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str | None = Form(default=None),
    MediaContentType0: str | None = Form(default=None),
    MessageSid: str | None = Form(default=None),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
):
    """Twilio WhatsApp webhook: validate, normalize, ingest, and return TwiML."""
    form_params = {key: str(value) for key, value in (await request.form()).items()}
    url = f"{get_settings().public_base_url}/api/webhooks/twilio/whatsapp"
    if not validate_twilio_signature(x_twilio_signature, url, form_params):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    message_type = MessageType.text
    if int(NumMedia or "0") > 0:
        message_type = (
            MessageType.voice if (MediaContentType0 or "").startswith("audio") else MessageType.image
        )

    await ingest_message(
        db,
        IngestMessageIn(
            phone=From.replace("whatsapp:", ""),
            message_type=message_type,
            text=Body or None,
            media_url=MediaUrl0,
            media_type=MediaContentType0,
            external_message_id=MessageSid,
            source="twilio_whatsapp",
        ),
    )
    return Response(content="<Response></Response>", media_type="application/xml")


# ── Orders ─────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=list[OrderOut])
def orders(
    db:          DbDep,
    store_id:    StoreDep,
    status:      OrderStatus | None = Query(default=None),
    customer_id: int | None         = Query(default=None),
    limit:       int                = Query(default=100, le=500),
    offset:      int                = Query(default=0),
):
    return list_orders(
        db, status=status, customer_id=customer_id, limit=limit, offset=offset, store_id=store_id
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
def order_detail(order_id: int, db: DbDep, store_id: StoreDep):
    try:
        return get_order(db, order_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def set_order_status(order_id: int, payload: StatusUpdateIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    try:
        return update_order_status(db, order_id, payload.status, store_id=store_id)
    except ValueError as exc:
        status_code = 400 if "Invalid order transition" in str(exc) else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/items", response_model=OrderOut)
def correct_order(
    order_id: int,
    payload: OrderCorrectionIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: StaffDep,
):
    try:
        return correct_order_items(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/review/resolve", response_model=OrderOut)
def resolve_review(
    order_id: int,
    payload: OrderReviewResolveIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: StaffDep,
):
    try:
        return resolve_order_review(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        status_code = 400 if "Review can only" in str(exc) or "Invalid order transition" in str(exc) else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/amount", response_model=OrderOut)
def set_order_amount(order_id: int, payload: AmountUpdateIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    try:
        return update_order_amount(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/notes", response_model=OrderOut)
def set_order_notes(order_id: int, payload: OrderNotesUpdateIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    try:
        return update_order_notes(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/repeat", response_model=OrderOut, status_code=201)
def create_repeat_order(order_id: int, payload: RepeatOrderIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    if not get_settings().repeat_orders_enabled:
        raise HTTPException(status_code=404, detail="Repeat orders are disabled")
    try:
        return repeat_order(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "Repeat orders" in str(exc) else 404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/staff-assignments", response_model=StaffAssignmentOut, status_code=201)
def create_staff_assignment(order_id: int, payload: StaffAssignmentIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    if not get_settings().staff_assignment_enabled:
        raise HTTPException(status_code=404, detail="Staff assignment is disabled")
    try:
        return assign_staff(db, order_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/staff-assignments", response_model=list[StaffAssignmentOut])
def staff_assignments(db: DbDep, store_id: StoreDep, order_id: int | None = Query(default=None), operator_id: int | None = Query(default=None)):
    return list_staff_assignments(db, store_id=store_id, order_id=order_id, operator_id=operator_id)


@router.patch("/staff-assignments/{assignment_id}", response_model=StaffAssignmentOut)
def edit_staff_assignment(assignment_id: int, payload: StaffAssignmentUpdateIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    try:
        return update_staff_assignment(db, assignment_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/confirmations", response_model=OutboundMessageOut, status_code=201)
def send_order_confirmation(
    order_id: int,
    payload: OutboundConfirmationIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: StaffDep,
):
    try:
        order = get_order(db, order_id, store_id=store_id)
        return create_outbound_confirmation(db, order, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Customers ──────────────────────────────────────────────────────────────────

@router.get("/customers", response_model=list[CustomerOut])
def customers(
    db:           DbDep,
    store_id:     StoreDep,
    dormant_only: bool = Query(default=False),
):
    result = []
    for c in list_customers(db, dormant_only=dormant_only, store_id=store_id):
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        result.append(out)
    return result


@router.post("/customers", response_model=CustomerOut, status_code=201)
def add_customer(payload: CustomerCreateIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    try:
        c = create_customer(db, payload, store_id=store_id)
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        return out
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def customer_detail(customer_id: int, db: DbDep, store_id: StoreDep):
    try:
        c, dormant = get_customer_with_dormant(db, customer_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    out = CustomerOut.model_validate(c)
    out.dormant = dormant
    return out


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
def edit_customer(
    customer_id: int,
    payload: CustomerUpdateIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: StaffDep,
):
    try:
        c = update_customer(db, customer_id, payload, store_id=store_id)
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/customers/{customer_id}/credit", response_model=CustomerOut)
def credit(customer_id: int, payload: CreditAdjustIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    try:
        c = adjust_credit(db, customer_id, payload, store_id=store_id)
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/ledger", response_model=list[LedgerEntryOut])
def ledger(customer_id: int, db: DbDep, store_id: StoreDep):
    try:
        return get_ledger(db, customer_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/history")
def customer_order_history(customer_id: int, db: DbDep, store_id: StoreDep, limit: int = Query(default=10, le=50)):
    try:
        return customer_history(db, customer_id, store_id=store_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Catalog ──────────────────────────────────────────────────────────────────

@router.get("/catalog/products", response_model=list[ProductOut])
def products(db: DbDep, store_id: StoreDep, status: ProductStatus | None = Query(default=None), q: str | None = Query(default=None), limit: int = Query(default=100, le=500), offset: int = Query(default=0)):
    if not get_settings().catalog_enabled:
        raise HTTPException(status_code=404, detail="Catalog is disabled")
    return list_products(db, store_id=store_id, status=status, q=q, limit=limit, offset=offset)


@router.post("/catalog/products", response_model=ProductOut, status_code=201)
def add_product(payload: ProductCreateIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    if not get_settings().catalog_enabled:
        raise HTTPException(status_code=404, detail="Catalog is disabled")
    try:
        return create_product(db, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/catalog/products/{product_id}", response_model=ProductOut)
def product_detail(product_id: int, db: DbDep, store_id: StoreDep):
    try:
        return get_product(db, product_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/catalog/products/{product_id}", response_model=ProductOut)
def edit_product(product_id: int, payload: ProductUpdateIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    try:
        return update_product(db, product_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 404, detail=str(exc)) from exc


@router.post("/catalog/products/{product_id}/substitutions", response_model=ProductSubstitutionOut, status_code=201)
def add_substitution(product_id: int, payload: ProductSubstitutionIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    try:
        return add_product_substitution(db, product_id, payload, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "cannot substitute" in str(exc) else 404, detail=str(exc)) from exc


@router.get("/catalog/products/{product_id}/substitutions", response_model=list[ProductSubstitutionOut])
def substitutions(product_id: int, db: DbDep, store_id: StoreDep):
    try:
        return list_product_substitutions(db, product_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Operations reporting and AI usage ────────────────────────────────────────

@router.get("/operations/daily-report", response_model=OperationsDailyReportOut)
def daily_report(db: DbDep, store_id: StoreDep, day: str | None = Query(default=None)):
    return operations_daily_report(db, store_id=store_id, day=day)


@router.post("/operations/ai-usage", response_model=AiUsageEventOut, status_code=201)
def add_ai_usage(payload: AiUsageEventCreateIn, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    if not get_settings().ai_usage_tracking_enabled:
        raise HTTPException(status_code=404, detail="AI usage tracking is disabled")
    return record_ai_usage(db, payload, store_id=store_id)


@router.get("/operations/ai-usage", response_model=list[AiUsageEventOut])
def list_ai_usage(db: DbDep, store_id: StoreDep, day: str | None = Query(default=None), limit: int = Query(default=100, le=1000)):
    return ai_usage_events(db, store_id=store_id, day=day, limit=limit)


@router.get("/operations/ai-usage/summary", response_model=AiUsageSummaryOut)
def usage_summary(db: DbDep, store_id: StoreDep, day: str | None = Query(default=None)):
    return ai_usage_summary(db, store_id=store_id, day=day)


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/daily", response_model=list[DailyMetric])
def analytics_daily(db: DbDep, store_id: StoreDep, days: int = Query(default=7, le=90)):
    return daily_metrics(db, days=days, store_id=store_id)


@router.get("/analytics/top-items", response_model=list[TopItem])
def analytics_top_items(
    db:    DbDep,
    store_id: StoreDep,
    days:  int = Query(default=30, le=365),
    limit: int = Query(default=10, le=50),
):
    return top_items(db, days=days, limit=limit, store_id=store_id)


@router.get("/analytics/input-methods", response_model=list[InputMethodStat])
def analytics_input_methods(db: DbDep, store_id: StoreDep, days: int = Query(default=30, le=365)):
    return input_method_stats(db, days=days, store_id=store_id)


# ── Delivery ─────────────────────────────────────────────────────────────────

@router.post("/delivery/agents", response_model=DeliveryAgentOut, status_code=201)
def add_delivery_agent(payload: DeliveryAgentCreateIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    return create_delivery_agent(db, store_id, payload)


@router.get("/delivery/agents", response_model=list[DeliveryAgentOut])
def delivery_agents(db: DbDep, store_id: StoreDep):
    return list_delivery_agents(db, store_id)


@router.post("/orders/{order_id}/delivery", response_model=DeliveryAssignmentOut, status_code=201)
def assign_order_delivery(
    order_id: int,
    payload: DeliveryAssignmentIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: ManagerDep,
):
    try:
        return assign_delivery(db, store_id, order_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/delivery/assignments/{assignment_id}/status", response_model=DeliveryAssignmentOut)
def set_delivery_status(
    assignment_id: int,
    payload: DeliveryAssignmentStatusIn,
    db: DbDep,
    store_id: StoreDep,
    _operator: StaffDep,
):
    try:
        return update_delivery_status(db, store_id, assignment_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/delivery/agents/{agent_id}/route", response_model=list[RouteStop])
def delivery_route(agent_id: int, db: DbDep, store_id: StoreDep):
    return route_for_agent(db, store_id, agent_id)


@router.post("/delivery/routes/optimize", response_model=RouteOptimizeOut)
def optimize_delivery_route(payload: RouteOptimizeIn, db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    return optimize_route(
        db,
        store_id,
        agent_id=payload.agent_id,
        order_ids=payload.order_ids,
        start_latitude=payload.start_latitude,
        start_longitude=payload.start_longitude,
    )


# ── Payments ─────────────────────────────────────────────────────────────────

@router.post("/payments/upi/webhook", response_model=PaymentOut, status_code=201)
async def upi_webhook(
    request: Request,
    payload: UpiWebhookIn,
    db: DbDep,
    store_id: StoreDep,
    x_kirana_signature: str | None = Header(default=None, alias="X-Kirana-Signature"),
    x_kirana_timestamp: str | None = Header(default=None, alias="X-Kirana-Timestamp"),
):
    body = await request.body()
    if not verify_upi_webhook_signature(body, x_kirana_signature, x_kirana_timestamp):
        raise HTTPException(status_code=403, detail="Invalid UPI webhook signature")
    try:
        return reconcile_upi_payment(db, store_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/payments/manual", response_model=PaymentOut, status_code=201)
def manual_payment(payload: ManualPaymentIn, db: DbDep, store_id: StoreDep, operator: ManagerDep):
    try:
        return record_manual_payment(db, store_id, payload, operator)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "not found" not in str(exc) else 404, detail=str(exc)) from exc


@router.get("/orders/{order_id}/payments/summary", response_model=OrderPaymentSummaryOut)
def payment_summary(order_id: int, db: DbDep, store_id: StoreDep, _operator: StaffDep):
    try:
        return order_payment_summary(db, store_id, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/refunds", response_model=RefundOut, status_code=201)
def create_refund(payload: RefundRequestIn, db: DbDep, store_id: StoreDep, operator: ManagerDep):
    try:
        return request_refund(db, store_id, payload, operator)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "not found" not in str(exc) else 404, detail=str(exc)) from exc


@router.post("/refunds/{refund_id}/decision", response_model=RefundOut)
def refund_decision(refund_id: int, payload: RefundDecisionIn, db: DbDep, store_id: StoreDep, operator: OwnerDep):
    try:
        return decide_refund(db, store_id, refund_id, payload.approve, payload.notes, operator)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "not found" not in str(exc) else 404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/financial-cancellation", response_model=OrderOut)
def financial_cancellation(order_id: int, payload: RefundDecisionIn, db: DbDep, store_id: StoreDep, operator: ManagerDep):
    reason = payload.notes or "Cancelled by operator"
    try:
        return cancel_order_financially(db, store_id, order_id, reason, operator)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "not found" not in str(exc) else 404, detail=str(exc)) from exc


@router.post("/settlements", response_model=SettlementOut, status_code=201)
def create_settlement(payload: SettlementGenerateIn, db: DbDep, store_id: StoreDep, operator: ManagerDep):
    return generate_settlement(db, store_id, payload.day, payload.notes, operator)


@router.get("/settlements", response_model=list[SettlementOut])
def settlements(db: DbDep, store_id: StoreDep, _operator: ManagerDep):
    return list_settlements(db, store_id)


@router.post("/settlements/{settlement_id}/close", response_model=SettlementOut)
def settlement_close(settlement_id: int, payload: SettlementCloseIn, db: DbDep, store_id: StoreDep, operator: OwnerDep):
    try:
        return close_settlement(db, store_id, settlement_id, payload.notes, operator)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/accounting/export")
def accounting_export(db: DbDep, store_id: StoreDep, _operator: ManagerDep, day: str | None = Query(default=None), format: str = Query(default="csv", pattern="^(csv|xlsx)$")):
    content, media_type, filename = export_accounting(db, store_id, day, format)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ── Audit ───────────────────────────────────────────────────────────────────

@router.get("/audit/events", response_model=list[AuditEventOut])
def audit_events(
    db: DbDep,
    store_id: StoreDep,
    _operator: ManagerDep,
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    return list_audit_events(
        db,
        store_id=store_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        since=since,
        until=until,
        limit=limit,
    )
