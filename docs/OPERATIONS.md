# Operations Guide

## Daily Flow

1. Review new WhatsApp orders.
2. Resolve `needs_review` orders before packing.
3. Move orders to `packed`.
4. Send outbound confirmation.
5. Assign delivery agent and route order.
6. Mark delivered.
7. Reconcile UPI or cash settlement against udhaari.

## Authority Model

| Workflow | Minimum role |
|---|---|
| Create stores | owner |
| Create operators | owner |
| Create customers | staff |
| Update order status | staff |
| Send confirmations | staff |
| Update amount or udhaari | manager |
| Manage delivery agents | manager |
| Optimize routes | manager |
| View audit events | manager |

## Evidence Model

KiranaOS records operational evidence for customer messages, parsed orders, order lifecycle changes, outbound messages, delivery assignments, route optimization, ledger entries, and UPI payments.

## Backup And Recovery

For production Postgres deployments, use managed database backups and verify restores periodically. For local SQLite demo mode, treat `backend/data/` as disposable.
