"""
Integration tests for the API.
Uses an in-memory SQLite database scoped to the test session.

The key issue with FastAPI + SQLAlchemy in-memory testing:
  - The app creates tables on its own engine at startup (main.py).
  - We override get_db() to use a different (test) engine.
  - So we must create tables on the TEST engine too, before any request.
  - Using a single shared in-memory DB URL with the same engine avoids the split.
"""

import os

# Point the app config at our test DB before any app imports
os.environ["KIRANA_DATABASE_URL"] = "sqlite:///./test_kiranaos.db"

import pytest
from fastapi.testclient import TestClient

# Import app after env is set — it will create tables on the test DB
from app.main import app
from app.db.session import Base, engine, get_db, SessionLocal


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables between tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ── Health ─────────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Ingest text order ──────────────────────────────────────────────────────────

def test_ingest_text_order_creates_order_and_items():
    res = client.post("/api/ingest/messages", json={
        "phone": "+919999990001",
        "customer_name": "Test Customer",
        "text": "2 kg atta, 1 l oil, bread",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert len(body["items"]) == 3
    assert body["customer"]["name"] == "Test Customer"


def test_ingest_creates_customer_on_first_message():
    client.post("/api/ingest/messages", json={
        "phone": "+919999990002",
        "customer_name": "New Customer",
        "text": "milk, eggs",
    })
    customers = client.get("/api/customers").json()
    phones = [c["phone"] for c in customers]
    assert "+919999990002" in phones


def test_ingest_upserts_existing_customer():
    """Two messages from same phone → one customer, two orders."""
    payload = {"phone": "+919999990003", "customer_name": "Repeat Customer", "text": "rice"}
    client.post("/api/ingest/messages", json=payload)
    client.post("/api/ingest/messages", json={**payload, "text": "dal"})

    customers = client.get("/api/customers").json()
    matching = [c for c in customers if c["phone"] == "+919999990003"]
    assert len(matching) == 1


def test_ingest_image_without_text_sets_needs_review():
    res = client.post("/api/ingest/messages", json={
        "phone": "+919999990004",
        "message_type": "image",
        "media_url": "https://example.invalid/list.jpg",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "needs_review"
    assert res.json()["notes"] is not None


def test_twilio_webhook_creates_order():
    res = client.post(
        "/api/webhooks/twilio/whatsapp",
        data={
            "From": "whatsapp:+919999990040",
            "Body": "2 kg atta, oil",
            "NumMedia": "0",
            "MessageSid": "SM123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    assert "<Response>" in res.text

    orders = client.get("/api/orders").json()
    assert any(o["customer"]["phone"] == "+919999990040" for o in orders)


def test_voice_without_transcription_sets_needs_review():
    res = client.post("/api/ingest/messages", json={
        "phone": "+919999990041",
        "message_type": "voice",
        "media_url": "https://example.invalid/order.ogg",
        "media_type": "audio/ogg",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "needs_review"
    assert "Voice note" in res.json()["notes"]


# ── Order status transitions ───────────────────────────────────────────────────

def test_advance_order_status():
    create_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990005",
        "customer_name": "Status Test",
        "text": "sugar 2kg",
    })
    order_id = create_res.json()["id"]

    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "packed"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "packed"

    deliver_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "delivered"})
    assert deliver_res.json()["status"] == "delivered"
    assert deliver_res.json()["delivered_at"] is not None


def test_invalid_status_rejected():
    create_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990006", "text": "soap"
    })
    order_id = create_res.json()["id"]
    res = client.patch(f"/api/orders/{order_id}/status", json={"status": "shipped"})
    assert res.status_code == 422


# ── Amount update ──────────────────────────────────────────────────────────────

def test_set_order_amount():
    create_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990007", "text": "atta"
    })
    order_id = create_res.json()["id"]
    res = client.patch(f"/api/orders/{order_id}/amount", json={"amount_due": 350.0, "is_credit": True})
    assert res.status_code == 200
    assert res.json()["amount_due"] == pytest.approx(350.0)
    assert res.json()["is_credit"] is True


def test_outbound_confirmation_is_recorded():
    create_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990008",
        "customer_name": "Confirm Test",
        "text": "bread",
    })
    order_id = create_res.json()["id"]

    res = client.post(
        f"/api/orders/{order_id}/confirmations",
        json={"body": "Order packed, Confirm Test ji!"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["order_id"] == order_id
    assert body["status"] == "simulated"
    assert body["destination_phone"] == "+919999990008"


# ── Customer management ────────────────────────────────────────────────────────

def test_create_customer_directly():
    res = client.post("/api/customers", json={
        "name": "Direct Customer",
        "phone": "+919999990010",
        "building": "Block A",
    })
    assert res.status_code == 201
    assert res.json()["name"] == "Direct Customer"


def test_duplicate_phone_rejected():
    client.post("/api/customers", json={"name": "First", "phone": "+919999990011"})
    res = client.post("/api/customers", json={"name": "Second", "phone": "+919999990011"})
    assert res.status_code == 409


def test_operator_login_returns_jwt():
    create = client.post("/api/operators", json={
        "username": "owner",
        "password": "supersecret",
        "role": "owner",
    })
    assert create.status_code == 201

    login = client.post("/api/auth/login", json={
        "username": "owner",
        "password": "supersecret",
    })
    assert login.status_code == 200
    assert login.json()["access_token"].count(".") == 2


def test_store_scoped_duplicate_phone_allowed_across_stores():
    from app.schemas.domain import CustomerCreateIn
    from app.services.ingestion import create_customer

    store = client.post("/api/stores", json={
        "name": "Second Store",
        "slug": "second-store",
    })
    assert store.status_code == 201
    second_store_id = store.json()["id"]

    db = SessionLocal()
    try:
        first = create_customer(db, CustomerCreateIn(name="One", phone="+919999990012"), store_id=1)
        second = create_customer(
            db,
            CustomerCreateIn(name="Two", phone="+919999990012"),
            store_id=second_store_id,
        )
    finally:
        db.close()
    assert first.phone == second.phone
    assert first.store_id != second.store_id


# ── Udhaari / credit ──────────────────────────────────────────────────────────

def test_extend_and_settle_credit():
    client.post("/api/ingest/messages", json={"phone": "+919999990020", "text": "rice"})
    customers = client.get("/api/customers").json()
    cid = next(c["id"] for c in customers if c["phone"] == "+919999990020")

    res = client.post(f"/api/customers/{cid}/credit", json={"amount": 500.0, "reason": "udhaari"})
    assert res.json()["credit_balance"] == pytest.approx(500.0)

    res = client.post(f"/api/customers/{cid}/credit", json={"amount": -200.0, "reason": "paid"})
    assert res.json()["credit_balance"] == pytest.approx(300.0)


def test_upi_payment_reconciles_credit_ledger():
    client.post("/api/ingest/messages", json={"phone": "+919999990022", "text": "rice"})
    customers = client.get("/api/customers").json()
    cid = next(c["id"] for c in customers if c["phone"] == "+919999990022")
    client.post(f"/api/customers/{cid}/credit", json={"amount": 500.0, "reason": "udhaari"})

    payment = client.post("/api/payments/upi/webhook", json={
        "provider_ref": "upi-ref-001",
        "amount": 200.0,
        "customer_id": cid,
        "payer_vpa": "customer@upi",
    })
    assert payment.status_code == 201
    assert payment.json()["status"] == "reconciled"

    customer = client.get(f"/api/customers/{cid}").json()
    assert customer["credit_balance"] == pytest.approx(300.0)


def test_delivery_assignment_and_route():
    order_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990023",
        "customer_name": "Route Customer",
        "building": "A-301",
        "text": "milk",
    })
    order_id = order_res.json()["id"]
    agent = client.post("/api/delivery/agents", json={"name": "Ramesh", "phone": "+919999991111"})
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    assignment = client.post(
        f"/api/orders/{order_id}/delivery",
        json={"agent_id": agent_id, "route_order": 1},
    )
    assert assignment.status_code == 201

    route = client.get(f"/api/delivery/agents/{agent_id}/route")
    assert route.status_code == 200
    assert route.json()[0]["order_id"] == order_id


def test_payment_cannot_exceed_balance():
    client.post("/api/ingest/messages", json={"phone": "+919999990021", "text": "tea"})
    customers = client.get("/api/customers").json()
    cid = next(c["id"] for c in customers if c["phone"] == "+919999990021")

    res = client.post(f"/api/customers/{cid}/credit", json={"amount": -1000.0, "reason": "overpay"})
    assert res.json()["credit_balance"] >= 0


# ── Dashboard summary ──────────────────────────────────────────────────────────

def test_dashboard_summary_structure():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    body = res.json()
    for key in ("pending", "packed", "delivered_today", "needs_review", "dormant_customers", "total_credit"):
        assert key in body


# ── Analytics ──────────────────────────────────────────────────────────────────

def test_analytics_daily_returns_list():
    res = client.get("/api/analytics/daily?days=7")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_analytics_top_items():
    client.post("/api/ingest/messages", json={"phone": "+919999990030", "text": "atta 5kg, doodh"})
    res = client.get("/api/analytics/top-items")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
