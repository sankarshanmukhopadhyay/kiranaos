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

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.domain import MessageType, OrderStatus
from app.schemas.domain import (
    AmountUpdateIn,
    CreditAdjustIn,
    CustomerCreateIn,
    CustomerOut,
    DailyMetric,
    DashboardSummary,
    IngestMessageIn,
    InputMethodStat,
    LedgerEntryOut,
    OrderOut,
    StatusUpdateIn,
    TopItem,
)
from app.services.adapters import validate_twilio_signature
from app.services.ingestion import (
    adjust_credit,
    create_customer,
    daily_metrics,
    dashboard_summary,
    get_customer_with_dormant,
    get_ledger,
    get_order,
    input_method_stats,
    ingest_message,
    list_customers,
    list_orders,
    top_items,
    update_order_amount,
    update_order_status,
    _is_dormant,
)

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": get_settings().app_name}


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/summary", response_model=DashboardSummary)
def summary(db: DbDep):
    return dashboard_summary(db)


# ── Ingestion ──────────────────────────────────────────────────────────────────

@router.post("/ingest/messages", response_model=OrderOut, status_code=201)
async def ingest(payload: IngestMessageIn, db: DbDep):
    """
    Normalised ingest endpoint. All provider adapters (Twilio, Meta) map their
    payloads to IngestMessageIn before calling this.
    """
    return await ingest_message(db, payload)


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
    status:      OrderStatus | None = Query(default=None),
    customer_id: int | None         = Query(default=None),
    limit:       int                = Query(default=100, le=500),
    offset:      int                = Query(default=0),
):
    return list_orders(db, status=status, customer_id=customer_id, limit=limit, offset=offset)


@router.get("/orders/{order_id}", response_model=OrderOut)
def order_detail(order_id: int, db: DbDep):
    try:
        return get_order(db, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def set_order_status(order_id: int, payload: StatusUpdateIn, db: DbDep):
    try:
        return update_order_status(db, order_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/orders/{order_id}/amount", response_model=OrderOut)
def set_order_amount(order_id: int, payload: AmountUpdateIn, db: DbDep):
    try:
        return update_order_amount(db, order_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Customers ──────────────────────────────────────────────────────────────────

@router.get("/customers", response_model=list[CustomerOut])
def customers(
    db:           DbDep,
    dormant_only: bool = Query(default=False),
):
    result = []
    for c in list_customers(db, dormant_only=dormant_only):
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        result.append(out)
    return result


@router.post("/customers", response_model=CustomerOut, status_code=201)
def add_customer(payload: CustomerCreateIn, db: DbDep):
    try:
        c = create_customer(db, payload)
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        return out
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def customer_detail(customer_id: int, db: DbDep):
    try:
        c, dormant = get_customer_with_dormant(db, customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    out = CustomerOut.model_validate(c)
    out.dormant = dormant
    return out


@router.post("/customers/{customer_id}/credit", response_model=CustomerOut)
def credit(customer_id: int, payload: CreditAdjustIn, db: DbDep):
    try:
        c = adjust_credit(db, customer_id, payload)
        out = CustomerOut.model_validate(c)
        out.dormant = _is_dormant(c.last_order_at)
        return out
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/ledger", response_model=list[LedgerEntryOut])
def ledger(customer_id: int, db: DbDep):
    try:
        return get_ledger(db, customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/daily", response_model=list[DailyMetric])
def analytics_daily(db: DbDep, days: int = Query(default=7, le=90)):
    return daily_metrics(db, days=days)


@router.get("/analytics/top-items", response_model=list[TopItem])
def analytics_top_items(
    db:    DbDep,
    days:  int = Query(default=30, le=365),
    limit: int = Query(default=10, le=50),
):
    return top_items(db, days=days, limit=limit)


@router.get("/analytics/input-methods", response_model=list[InputMethodStat])
def analytics_input_methods(db: DbDep, days: int = Query(default=30, le=365)):
    return input_method_stats(db, days=days)
