---
layout: default
title: v2.5.0 Release 3
parent: Releases
nav_order: 2
permalink: /releases/v2.5.0/
---

# KiranaOS v2.5.0: Release 3 Order-to-Cash

Release 3 converts KiranaOS operational activity into controlled financial evidence. The release introduces tender-aware payment capture, payment-to-order reconciliation, manager-requested and owner-approved refunds, financial cancellation controls, closeable daily settlements, and accountant-ready CSV/XLSX exports.

## Release outcome

A pilot store can now move an order from intake through fulfillment and into a traceable cash, UPI, or split-tender financial record. Every sensitive mutation produces an audit event, and irreversible financial decisions are separated by operator role.

## Authority model

| Action | Minimum role | Evidence produced |
|---|---|---|
| Record cash, UPI, or split payment | Manager | Payment record and audit event |
| View order payment summary | Staff | Computed paid, refunded, net, and outstanding totals |
| Request refund | Manager | Pending refund request and audit event |
| Approve or reject refund | Owner | Refund decision, payment status update, audit event |
| Cancel an undelivered order | Manager | Cancellation reason and audit event |
| Generate settlement | Manager | Recomputed daily tender totals |
| Close settlement | Owner | Immutable closed status, closer identity, timestamp |
| Export accounting data | Manager | CSV or XLSX handoff artifact |

## New API surfaces

- `POST /api/payments/manual`
- `GET /api/orders/{order_id}/payments/summary`
- `POST /api/refunds`
- `POST /api/refunds/{refund_id}/decision`
- `POST /api/orders/{order_id}/financial-cancellation`
- `POST /api/settlements`
- `GET /api/settlements`
- `POST /api/settlements/{settlement_id}/close`
- `GET /api/accounting/export?format=csv|xlsx`

## Financial invariants

- A payment cannot exceed the current order outstanding amount.
- A split payment must contain positive cash and UPI components whose sum equals the payment amount.
- UPI payments require a unique provider reference.
- Refund requests cannot exceed the remaining refundable balance after pending requests.
- Only an owner can approve or reject a refund or close a settlement.
- A closed settlement is not recomputed by later generation calls.
- Delivered orders cannot be converted into cancellations; they require the refund workflow.

## Migration

Apply Alembic revision `20260724_0900_release3_order_to_cash.py` after the Release 2 migration.

```bash
cd backend
alembic upgrade head
```

## Validation evidence

- Backend compilation: passed.
- Core backend API and parser suite: 57 tests passed.
- New Release 3 tests cover split tender, overpayment rejection, refund decisioning, settlement closure, CSV export, and XLSX export.
- Full adapter-suite execution requires the declared `respx` development dependency.
