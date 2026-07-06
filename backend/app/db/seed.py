"""
seed.py — Populate the database with realistic demo data.

Run with: python -m app.db.seed
The seed is idempotent: re-running it skips customers that already exist.
"""

import asyncio

from app.db.session import Base, SessionLocal, engine
from app.models.domain import MessageType
from app.schemas.domain import CreditAdjustIn, IngestMessageIn
from app.services.ingestion import adjust_credit, ingest_message

SAMPLE_ORDERS = [
    IngestMessageIn(
        phone="+919800111111", customer_name="Sunita Sharma",
        building="Bldg A, Flat 302", language="hi",
        text="atta 5kg, toor dal 1kg, sarson ka tel 1L, namak",
    ),
    IngestMessageIn(
        phone="+919800222222", customer_name="Krishnamurthy",
        building="Bldg B, Flat 101", language="te",
        message_type=MessageType.voice,
        media_url="https://example.invalid/voice1.ogg",
        text="rice 5kg, curd 500g, tomatoes 1kg",   # pre-transcribed for demo
    ),
    IngestMessageIn(
        phone="+919800333333", customer_name="Meera Patel",
        building="Bldg C, Flat 204", language="hi",
        message_type=MessageType.image,
        media_url="https://example.invalid/list1.jpg",
        text="rice 10kg, toor dal 2kg, tel 5L, masala",
    ),
    IngestMessageIn(
        phone="+919800444444", customer_name="Ravi Shankar",
        building="Bldg A, Flat 105", language="hi",
        text="Maggi 12 packet, amul butter, bread, anda 12",
    ),
    IngestMessageIn(
        phone="+919800555555", customer_name="Ayesha Begum",
        building="Bldg D, Flat 401", language="hi",
        text="maida 1kg, ghee 500g, biscuits 2 packet",
    ),
    IngestMessageIn(
        phone="+919800666666", customer_name="Deepak Joshi",
        building="Bldg B, Flat 302", language="hi",
        text="moong dal 2kg, cheeni 2kg, chai powder 1 packet",
    ),
    IngestMessageIn(
        phone="+919800777777", customer_name="Lakshmi Devi",
        building="Bldg E, Flat 201", language="te",
        text="atta 10kg, poha 1kg, coconut oil 1L",
    ),
    IngestMessageIn(
        phone="+919800888888", customer_name="Farhan Ahmed",
        building="Bldg C, Flat 105", language="hi",
        text="besan 1kg, namkeen 2 packet, bisleri 1L",
    ),
    IngestMessageIn(
        phone="+919800999999", customer_name="Priya Nair",
        building="Bldg A, Flat 501", language="ml",
        text="idli rava 1kg, urad dal 500g, coconut 1, curry leaves",
    ),
    IngestMessageIn(
        phone="+919801010101", customer_name="Suresh Reddy",
        building="Bldg F, Flat 102", language="te",
        text="chana dal 1kg, rajma 500g, jeera 100g, haldi 100g",
    ),
]

UDHAARI_SEED = {
    "+919800111111": 340.0,
    "+919800333333": 210.0,
    "+919800555555": 500.0,
    "+919800777777": 120.0,
    "+919801010101": 970.0,
}


async def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models.domain import Customer

        for payload in SAMPLE_ORDERS:
            existing = db.scalar(select(Customer).where(Customer.phone == payload.phone))
            if existing:
                continue
            order = await ingest_message(db, payload)
            print(f"  Created order {order.id} for {payload.customer_name}")

        # Seed udhaari balances
        for phone, amount in UDHAARI_SEED.items():
            customer = db.scalar(select(Customer).where(Customer.phone == phone))
            if customer and customer.credit_balance == 0:
                adjust_credit(db, customer.id, CreditAdjustIn(
                    amount=amount,
                    reason="Opening udhaari balance (seed)",
                ))
                print(f"  Udhaari ₹{amount} set for {customer.name}")

        print(f"\nSeed complete. {len(SAMPLE_ORDERS)} orders, {len(UDHAARI_SEED)} udhaari balances.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run())
