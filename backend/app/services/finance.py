"""Release 3 order-to-cash controls and accounting evidence."""

from __future__ import annotations

import csv
from datetime import date, datetime, time, timezone
from io import BytesIO, StringIO

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.domain import (
    AuditAction, DailySettlement, Order, OrderStatus, Payment, PaymentMethod,
    PaymentStatus, Refund, RefundStatus, SettlementStatus,
)
from app.schemas.domain import ManualPaymentIn, RefundRequestIn
from app.services.audit import record_audit_event


def _actor(operator: object | None) -> str | None:
    return str(getattr(operator, "id", "demo")) if operator is not None else "demo"


def _day_bounds(day: str | None) -> tuple[str, datetime, datetime]:
    target = date.fromisoformat(day) if day else datetime.now(timezone.utc).date()
    start = datetime.combine(target, time.min, tzinfo=timezone.utc)
    end = datetime.combine(target, time.max, tzinfo=timezone.utc)
    return target.isoformat(), start, end


def record_manual_payment(db: Session, store_id: int, payload: ManualPaymentIn, operator: object | None) -> Payment:
    order = db.scalar(select(Order).where(Order.id == payload.order_id, Order.store_id == store_id))
    if not order:
        raise ValueError(f"Order {payload.order_id} not found")
    if order.status == OrderStatus.cancelled:
        raise ValueError("Cannot record payment against a cancelled order")
    cash = payload.cash_amount
    upi = payload.upi_amount
    if payload.method == PaymentMethod.cash:
        cash, upi = payload.amount, 0.0
    elif payload.method == PaymentMethod.upi:
        cash, upi = 0.0, payload.amount
        if not payload.provider_ref:
            raise ValueError("UPI payments require provider_ref")
    elif round(cash + upi, 2) != round(payload.amount, 2) or cash <= 0 or upi <= 0:
        raise ValueError("Split payment cash_amount and upi_amount must be positive and equal amount")

    summary = order_payment_summary(db, store_id, order.id)
    if payload.amount > summary["outstanding"] + 0.001:
        raise ValueError("Payment exceeds order outstanding amount")
    ref = payload.provider_ref or f"cash-{store_id}-{order.id}-{int(datetime.now(timezone.utc).timestamp()*1000)}"
    if db.scalar(select(Payment).where(Payment.store_id == store_id, Payment.provider_ref == ref)):
        raise ValueError("Payment reference already exists")
    payment = Payment(store_id=store_id, customer_id=order.customer_id, order_id=order.id,
        provider="manual", provider_ref=ref, amount=payload.amount, method=payload.method,
        cash_amount=cash, upi_amount=upi, payer_vpa=payload.payer_vpa,
        notes=payload.notes, status=PaymentStatus.reconciled, reconciled_at=datetime.now(timezone.utc))
    db.add(payment)
    record_audit_event(db, store_id=store_id, action=AuditAction.payment_recorded,
        entity_type="payment", entity_id=ref,
        actor_type="operator", actor_id=_actor(operator),
        evidence={"order_id": order.id, "amount": payload.amount, "method": payload.method.value})
    db.commit(); db.refresh(payment)
    return payment


def order_payment_summary(db: Session, store_id: int, order_id: int) -> dict:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.store_id == store_id))
    if not order:
        raise ValueError(f"Order {order_id} not found")
    payments = list(db.scalars(select(Payment).where(Payment.store_id == store_id, Payment.order_id == order_id).order_by(Payment.received_at)).all())
    paid = round(sum(p.amount for p in payments if p.status not in {PaymentStatus.failed, PaymentStatus.duplicate}), 2)
    refunded = round(sum(p.refunded_amount for p in payments), 2)
    net = round(paid - refunded, 2)
    outstanding = round(max(order.amount_due - net, 0.0), 2)
    status = "unpaid" if net <= 0 else ("paid" if outstanding <= 0 else "partially_paid")
    return {"order_id": order.id, "amount_due": order.amount_due, "paid_total": paid,
        "refunded_total": refunded, "net_paid": net, "outstanding": outstanding,
        "status": status, "payments": payments}


def request_refund(db: Session, store_id: int, payload: RefundRequestIn, operator: object | None) -> Refund:
    payment = db.scalar(select(Payment).where(Payment.id == payload.payment_id, Payment.store_id == store_id))
    if not payment:
        raise ValueError(f"Payment {payload.payment_id} not found")
    available = round(payment.amount - payment.refunded_amount, 2)
    pending = float(db.scalar(select(func.coalesce(func.sum(Refund.amount), 0.0)).where(
        Refund.payment_id == payment.id, Refund.status == RefundStatus.requested)) or 0.0)
    if payload.amount > round(available - pending, 2) + 0.001:
        raise ValueError("Refund exceeds refundable payment balance")
    refund = Refund(store_id=store_id, payment_id=payment.id, order_id=payment.order_id,
        amount=payload.amount, reason=payload.reason, requested_by=_actor(operator))
    db.add(refund)
    record_audit_event(db, store_id=store_id, action=AuditAction.refund_requested,
        entity_type="refund", entity_id=f"payment:{payment.id}", actor_type="operator",
        actor_id=_actor(operator), evidence={"amount": payload.amount, "reason": payload.reason})
    db.commit(); db.refresh(refund)
    return refund


def decide_refund(db: Session, store_id: int, refund_id: int, approve: bool, notes: str | None, operator: object | None) -> Refund:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id, Refund.store_id == store_id))
    if not refund:
        raise ValueError(f"Refund {refund_id} not found")
    if refund.status != RefundStatus.requested:
        raise ValueError("Refund has already been decided")
    refund.decided_by = _actor(operator); refund.decided_at = datetime.now(timezone.utc)
    payment = db.get(Payment, refund.payment_id)
    if approve:
        if not payment or refund.amount > payment.amount - payment.refunded_amount + 0.001:
            raise ValueError("Refund exceeds refundable payment balance")
        refund.status = RefundStatus.approved
        payment.refunded_amount = round(payment.refunded_amount + refund.amount, 2)
        payment.status = PaymentStatus.refunded if payment.refunded_amount >= payment.amount else PaymentStatus.partially_refunded
        action = AuditAction.refund_approved
    else:
        refund.status = RefundStatus.rejected; action = AuditAction.refund_rejected
    if notes: refund.reason = f"{refund.reason} | Decision: {notes}"
    record_audit_event(db, store_id=store_id, action=action, entity_type="refund", entity_id=refund.id,
        actor_type="operator", actor_id=_actor(operator), evidence={"amount": refund.amount})
    db.commit(); db.refresh(refund)
    return refund


def cancel_order_financially(db: Session, store_id: int, order_id: int, reason: str, operator: object | None) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.store_id == store_id))
    if not order: raise ValueError(f"Order {order_id} not found")
    if order.status == OrderStatus.delivered: raise ValueError("Delivered orders require refund handling, not cancellation")
    order.status = OrderStatus.cancelled
    order.notes = f"{order.notes + ' | ' if order.notes else ''}Cancellation: {reason}"
    record_audit_event(db, store_id=store_id, action=AuditAction.order_cancelled_financially,
        entity_type="order", entity_id=order.id, actor_type="operator", actor_id=_actor(operator), evidence={"reason": reason})
    db.commit(); db.refresh(order); return order


def generate_settlement(db: Session, store_id: int, day: str | None, notes: str | None, operator: object | None) -> DailySettlement:
    business_day, start, end = _day_bounds(day)
    payments = list(db.scalars(select(Payment).where(Payment.store_id == store_id, Payment.received_at.between(start, end),
        Payment.status.notin_([PaymentStatus.failed, PaymentStatus.duplicate]))).all())
    cash = round(sum(p.cash_amount for p in payments), 2); upi = round(sum(p.upi_amount for p in payments), 2)
    refunds = float(db.scalar(select(func.coalesce(func.sum(Refund.amount), 0.0)).where(
        Refund.store_id == store_id, Refund.status == RefundStatus.approved, Refund.decided_at.between(start, end))) or 0.0)
    settlement = db.scalar(select(DailySettlement).where(DailySettlement.store_id == store_id, DailySettlement.business_day == business_day))
    if settlement and settlement.status == SettlementStatus.closed:
        return settlement
    if not settlement:
        settlement = DailySettlement(store_id=store_id, business_day=business_day); db.add(settlement)
    settlement.cash_total=cash; settlement.upi_total=upi; settlement.refund_total=round(refunds,2)
    settlement.net_total=round(cash+upi-refunds,2); settlement.payment_count=len(payments); settlement.notes=notes
    record_audit_event(db, store_id=store_id, action=AuditAction.settlement_generated,
        entity_type="daily_settlement", entity_id=business_day, actor_type="operator", actor_id=_actor(operator),
        evidence={"cash_total": cash, "upi_total": upi, "refund_total": refunds})
    db.commit(); db.refresh(settlement); return settlement


def close_settlement(db: Session, store_id: int, settlement_id: int, notes: str | None, operator: object | None) -> DailySettlement:
    settlement = db.scalar(select(DailySettlement).where(DailySettlement.id == settlement_id, DailySettlement.store_id == store_id))
    if not settlement: raise ValueError(f"Settlement {settlement_id} not found")
    if settlement.status == SettlementStatus.closed: return settlement
    settlement.status=SettlementStatus.closed; settlement.closed_at=datetime.now(timezone.utc); settlement.closed_by=_actor(operator)
    if notes: settlement.notes = notes
    record_audit_event(db, store_id=store_id, action=AuditAction.settlement_closed,
        entity_type="daily_settlement", entity_id=settlement.id, actor_type="operator", actor_id=_actor(operator),
        evidence={"net_total": settlement.net_total, "business_day": settlement.business_day})
    db.commit(); db.refresh(settlement); return settlement


def list_settlements(db: Session, store_id: int) -> list[DailySettlement]:
    return list(db.scalars(select(DailySettlement).where(DailySettlement.store_id == store_id).order_by(DailySettlement.business_day.desc())).all())


def accounting_rows(db: Session, store_id: int, day: str | None) -> list[dict]:
    _, start, end = _day_bounds(day)
    payments = db.scalars(select(Payment).where(Payment.store_id == store_id, Payment.received_at.between(start,end)).order_by(Payment.received_at)).all()
    return [{"date": p.received_at.isoformat(), "type": "payment", "reference": p.provider_ref,
        "order_id": p.order_id or "", "customer_id": p.customer_id or "", "method": p.method.value,
        "gross_amount": p.amount, "refund_amount": p.refunded_amount, "net_amount": round(p.amount-p.refunded_amount,2),
        "status": p.status.value, "notes": p.notes or ""} for p in payments]


def export_accounting(db: Session, store_id: int, day: str | None, fmt: str) -> tuple[bytes, str, str]:
    rows=accounting_rows(db,store_id,day); fields=["date","type","reference","order_id","customer_id","method","gross_amount","refund_amount","net_amount","status","notes"]
    suffix = day or datetime.now(timezone.utc).date().isoformat()
    if fmt == "csv":
        out=StringIO(); w=csv.DictWriter(out,fieldnames=fields); w.writeheader(); w.writerows(rows)
        return out.getvalue().encode(), "text/csv", f"kiranaos-accounting-{suffix}.csv"
    wb=Workbook(); ws=wb.active; ws.title="Order-to-Cash"; ws.append(fields)
    for row in rows: ws.append([row[x] for x in fields])
    out=BytesIO(); wb.save(out)
    return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"kiranaos-accounting-{suffix}.xlsx"
