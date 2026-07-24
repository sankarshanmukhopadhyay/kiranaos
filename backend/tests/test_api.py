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

from app.db.session import Base, SessionLocal, engine

# Import app after env is set — it will create tables on the test DB
from app.main import app


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
    assert body["provider"] == "simulation"
    assert body["dispatch_attempts"] == 1
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


def test_route_optimization_updates_route_order_and_records_strategy():
    agent = client.post("/api/delivery/agents", json={"name": "Route Agent", "phone": "+919999991112"})
    agent_id = agent.json()["id"]
    orders = []
    for idx, building in enumerate(["C-301", "A-101", "B-201"], start=1):
        order_res = client.post("/api/ingest/messages", json={
            "phone": f"+91999999006{idx}",
            "customer_name": f"Route Customer {idx}",
            "building": building,
            "text": "milk",
        })
        order_id = order_res.json()["id"]
        orders.append(order_id)
        client.post(f"/api/orders/{order_id}/delivery", json={"agent_id": agent_id, "route_order": idx})

    optimized = client.post("/api/delivery/routes/optimize", json={"agent_id": agent_id})
    assert optimized.status_code == 200
    body = optimized.json()
    assert body["strategy"] == "address_sort_fallback"
    assert sorted(body["ordered_order_ids"]) == sorted(orders)
    assert [stop["route_order"] for stop in body["stops"]] == [1, 2, 3]


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

# ── Security hardening ───────────────────────────────────────────────────────

def test_unsafe_media_url_is_rejected_to_needs_review_without_fetch():
    res = client.post("/api/ingest/messages", json={
        "phone": "+919999990050",
        "message_type": "voice",
        "media_url": "http://127.0.0.1:8000/internal.ogg",
        "media_type": "audio/ogg",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "needs_review"


def test_jwt_rejects_tampered_signature():
    create = client.post("/api/operators", json={
        "username": "security-owner",
        "password": "supersecret",
        "role": "owner",
    })
    assert create.status_code == 201
    login = client.post("/api/auth/login", json={
        "username": "security-owner",
        "password": "supersecret",
    })
    token = login.json()["access_token"]
    parts = token.split(".")
    bad = ".".join([parts[0], parts[1], "tampered"])

    from fastapi import HTTPException

    from app.services.auth import decode_access_token
    with pytest.raises(HTTPException):
        decode_access_token(bad)


def test_upi_duplicate_is_scoped_to_current_store():
    from app.models.domain import Payment
    from app.schemas.domain import UpiWebhookIn
    from app.services.operations import reconcile_upi_payment

    store = client.post("/api/stores", json={"name": "Payment Store", "slug": "payment-store"})
    assert store.status_code == 201
    second_store_id = store.json()["id"]

    db = SessionLocal()
    try:
        first = reconcile_upi_payment(db, 1, UpiWebhookIn(provider_ref="same-ref", amount=100))
        second = reconcile_upi_payment(db, second_store_id, UpiWebhookIn(provider_ref="same-ref", amount=200))
        assert first.store_id == 1
        assert second.store_id == second_store_id
        assert first.id != second.id
        assert len(db.query(Payment).filter(Payment.provider_ref == "same-ref").all()) == 2
    finally:
        db.close()


def test_audit_events_are_created_for_order_mutations():
    create_res = client.post("/api/ingest/messages", json={
        "phone": "+919999990070",
        "customer_name": "Audit Test",
        "text": "sugar",
    })
    order_id = create_res.json()["id"]
    client.patch(f"/api/orders/{order_id}/status", json={"status": "packed"})

    events = client.get(f"/api/audit/events?entity_type=order&entity_id={order_id}")
    assert events.status_code == 200
    actions = [event["action"] for event in events.json()]
    assert "order_status_updated" in actions

# ── Release 1 commercial foundation ──────────────────────────────────────────

def test_duplicate_external_message_id_returns_existing_order_and_audit_event():
    payload = {
        "phone": "+919999990080",
        "customer_name": "Duplicate Test",
        "text": "2 kg atta",
        "source": "twilio_whatsapp",
        "external_message_id": "SM-DUP-1",
    }
    first = client.post("/api/ingest/messages", json=payload)
    second = client.post("/api/ingest/messages", json={**payload, "text": "5 kg rice"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    events = client.get("/api/audit/events?action=duplicate_message_ignored")
    assert events.status_code == 200
    assert any(event["action"] == "duplicate_message_ignored" for event in events.json())


def test_review_order_can_be_resolved_with_corrected_items():
    create = client.post("/api/ingest/messages", json={
        "phone": "+919999990081",
        "message_type": "image",
        "media_url": "https://example.invalid/list.jpg",
    })
    order_id = create.json()["id"]
    assert create.json()["status"] == "needs_review"

    resolved = client.post(f"/api/orders/{order_id}/review/resolve", json={
        "items": [{"name": "Atta", "quantity": 5, "unit": "kg", "confidence": 1}],
        "notes": "Reviewed from image",
        "status": "pending",
    })
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "pending"
    assert resolved.json()["items"][0]["name"] == "Atta"

    events = client.get(f"/api/audit/events?entity_type=order&entity_id={order_id}")
    actions = [event["action"] for event in events.json()]
    assert "order_review_resolved" in actions
    assert "order_items_corrected" in actions


def test_invalid_order_transition_is_rejected():
    create = client.post("/api/ingest/messages", json={"phone": "+919999990082", "text": "2 kg sugar"})
    order_id = create.json()["id"]
    delivered = client.patch(f"/api/orders/{order_id}/status", json={"status": "delivered"})
    assert delivered.status_code == 400


def test_customer_update_is_audited():
    create = client.post("/api/customers", json={"name": "Editable", "phone": "+919999990083"})
    customer_id = create.json()["id"]
    updated = client.patch(f"/api/customers/{customer_id}", json={"building": "Block Z", "language_hint": "hi"})
    assert updated.status_code == 200
    assert updated.json()["building"] == "Block Z"

    events = client.get(f"/api/audit/events?entity_type=customer&entity_id={customer_id}&action=customer_updated")
    assert events.status_code == 200
    assert events.json()[0]["action"] == "customer_updated"


def test_daily_closing_returns_pilot_summary():
    client.post("/api/ingest/messages", json={"phone": "+919999990084", "text": "2 kg rice"})
    closing = client.get("/api/dashboard/daily-closing")
    assert closing.status_code == 200
    body = closing.json()
    assert body["orders_created"] >= 1
    assert "amount_due_total" in body

# ── Release 2 Operations Release ─────────────────────────────────────────────

def test_feature_flags_expose_operations_capabilities():
    res = client.get("/api/features")
    assert res.status_code == 200
    body = res.json()
    assert body["catalog_enabled"] is True
    assert body["staff_assignment_enabled"] is True
    assert body["repeat_orders_enabled"] is True
    assert body["ai_usage_tracking_enabled"] is True


def test_catalog_product_crud_and_substitution_are_audited():
    primary = client.post("/api/catalog/products", json={
        "sku": "ATTA-5KG",
        "name": "Atta 5kg",
        "category": "staples",
        "unit": "bag",
        "price": 260,
        "stock_quantity": 12,
    })
    assert primary.status_code == 201
    product_id = primary.json()["id"]

    substitute = client.post("/api/catalog/products", json={
        "sku": "ATTA-10KG",
        "name": "Atta 10kg",
        "category": "staples",
        "unit": "bag",
        "price": 510,
    })
    assert substitute.status_code == 201

    updated = client.patch(f"/api/catalog/products/{product_id}", json={"stock_quantity": 9, "notes": "Fast moving item"})
    assert updated.status_code == 200
    assert updated.json()["stock_quantity"] == pytest.approx(9)

    sub = client.post(
        f"/api/catalog/products/{product_id}/substitutions",
        json={"substitute_product_id": substitute.json()["id"], "reason": "larger pack available"},
    )
    assert sub.status_code == 201

    events = client.get(f"/api/audit/events?entity_type=product&entity_id={product_id}")
    actions = [event["action"] for event in events.json()]
    assert "product_created" in actions
    assert "product_updated" in actions
    assert "product_substitution_added" in actions


def test_order_item_correction_can_bind_catalog_product_and_notes():
    product = client.post("/api/catalog/products", json={"sku": "OIL-1L", "name": "Sunflower Oil 1L", "unit": "bottle"})
    order = client.post("/api/ingest/messages", json={"phone": "+919999990090", "text": "oil"})
    order_id = order.json()["id"]

    corrected = client.patch(f"/api/orders/{order_id}/items", json={
        "items": [{
            "name": "Sunflower Oil 1L",
            "quantity": 1,
            "unit": "bottle",
            "confidence": 1,
            "product_id": product.json()["id"],
            "notes": "Catalog matched by operator",
        }],
        "notes": "Ready to pack",
    })
    assert corrected.status_code == 200
    assert corrected.json()["items"][0]["product_id"] == product.json()["id"]
    assert corrected.json()["items"][0]["notes"] == "Catalog matched by operator"


def test_repeat_order_and_customer_history_support_daily_workflow():
    original = client.post("/api/ingest/messages", json={"phone": "+919999990091", "customer_name": "Repeat Buyer", "text": "bread, milk"})
    order_id = original.json()["id"]
    customer_id = original.json()["customer"]["id"]

    repeated = client.post(f"/api/orders/{order_id}/repeat", json={"notes": "Customer asked for same order again"})
    assert repeated.status_code == 201
    assert repeated.json()["customer"]["id"] == customer_id
    assert [item["name"] for item in repeated.json()["items"]] == [item["name"] for item in original.json()["items"]]

    history = client.get(f"/api/customers/{customer_id}/history")
    assert history.status_code == 200
    assert history.json()["lifetime_orders"] >= 2
    assert len(history.json()["recent_orders"]) >= 2


def test_staff_assignment_lifecycle_is_audited():
    operator = client.post("/api/operators", json={"username": "packer", "password": "supersecret", "role": "staff"})
    assert operator.status_code == 201
    order = client.post("/api/ingest/messages", json={"phone": "+919999990092", "text": "rice 5kg"})
    order_id = order.json()["id"]

    assignment = client.post(f"/api/orders/{order_id}/staff-assignments", json={
        "operator_id": operator.json()["id"],
        "role": "packing",
        "notes": "Pack before 6pm",
    })
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    updated = client.patch(f"/api/staff-assignments/{assignment_id}", json={"status": "completed", "notes": "Packed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"

    listed = client.get(f"/api/staff-assignments?order_id={order_id}")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == assignment_id

    events = client.get(f"/api/audit/events?entity_type=order&entity_id={order_id}")
    actions = [event["action"] for event in events.json()]
    assert "staff_assignment_created" in actions
    assert "staff_assignment_updated" in actions


def test_order_notes_ai_usage_and_operations_daily_report():
    order = client.post("/api/ingest/messages", json={"phone": "+919999990093", "text": "tea, sugar"})
    order_id = order.json()["id"]

    notes = client.patch(f"/api/orders/{order_id}/notes", json={"notes": "Customer prefers evening delivery"})
    assert notes.status_code == 200
    assert notes.json()["notes"] == "Customer prefers evening delivery"

    usage = client.post("/api/operations/ai-usage", json={
        "provider": "openai",
        "model": "gpt-4o-mini",
        "purpose": "parse",
        "order_id": order_id,
        "estimated_units": 42,
        "estimated_cost": 0.002,
        "success": True,
    })
    assert usage.status_code == 201

    summary = client.get("/api/operations/ai-usage/summary")
    assert summary.status_code == 200
    assert summary.json()["total_events"] >= 1
    assert summary.json()["by_provider"]["openai"] >= 1

    report = client.get("/api/operations/daily-report")
    assert report.status_code == 200
    body = report.json()
    assert body["orders_created"] >= 1
    assert "average_order_value" in body
    assert body["ai_usage_count"] >= 1


# ── Release 3 order-to-cash ──────────────────────────────────────────────────

def _order_with_amount(amount=500.0):
    order = client.post("/api/ingest/messages", json={"phone": "+919900000301", "text": "rice"}).json()
    client.patch(f"/api/orders/{order['id']}/amount", json={"amount_due": amount, "is_credit": False})
    return order["id"]

def test_manual_split_payment_and_summary():
    order_id = _order_with_amount()
    payment = client.post("/api/payments/manual", json={"order_id": order_id, "amount": 500, "method": "split", "cash_amount": 200, "upi_amount": 300, "provider_ref": "upi-r3-1"})
    assert payment.status_code == 201
    assert payment.json()["cash_amount"] == 200
    summary = client.get(f"/api/orders/{order_id}/payments/summary").json()
    assert summary["status"] == "paid"
    assert summary["outstanding"] == 0

def test_refund_requires_decision_and_updates_payment():
    order_id = _order_with_amount(300)
    payment = client.post("/api/payments/manual", json={"order_id": order_id, "amount": 300, "method": "cash"}).json()
    refund = client.post("/api/refunds", json={"payment_id": payment["id"], "amount": 100, "reason": "Item unavailable"})
    assert refund.status_code == 201 and refund.json()["status"] == "requested"
    decided = client.post(f"/api/refunds/{refund.json()['id']}/decision", json={"approve": True, "notes": "Cash returned"})
    assert decided.json()["status"] == "approved"
    summary = client.get(f"/api/orders/{order_id}/payments/summary").json()
    assert summary["refunded_total"] == 100
    assert summary["outstanding"] == 100

def test_daily_settlement_and_accounting_exports():
    order_id = _order_with_amount(125)
    client.post("/api/payments/manual", json={"order_id": order_id, "amount": 125, "method": "cash"})
    settlement = client.post("/api/settlements", json={}).json()
    assert settlement["cash_total"] == 125
    assert settlement["net_total"] == 125
    closed = client.post(f"/api/settlements/{settlement['id']}/close", json={"notes": "Till verified"})
    assert closed.json()["status"] == "closed"
    csv_res = client.get("/api/accounting/export?format=csv")
    assert csv_res.status_code == 200 and "gross_amount" in csv_res.text
    xlsx_res = client.get("/api/accounting/export?format=xlsx")
    assert xlsx_res.status_code == 200 and xlsx_res.content[:2] == b"PK"

def test_payment_cannot_exceed_outstanding():
    order_id = _order_with_amount(100)
    res = client.post("/api/payments/manual", json={"order_id": order_id, "amount": 101, "method": "cash"})
    assert res.status_code == 400
