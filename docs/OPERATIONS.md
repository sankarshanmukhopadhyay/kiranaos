---
layout: page
title: Operations Guide
permalink: /operations/
---

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

## Release 2 operations workflow

Release 2 expands the daily operating loop from review-only pilots to store workflow pilots.

### Daily loop

1. Review new orders.
2. Correct ambiguous items.
3. Link corrected items to catalog products where useful.
4. Record substitutions explicitly.
5. Assign fulfillment work to staff.
6. Create repeat orders for returning customers.
7. Review the daily operations report.
8. Inspect AI usage as a cost and reliability signal.

### Operational controls

- Product changes are audited.
- Substitution choices are explicit records.
- Repeat orders create new orders and audit events.
- Staff assignments are lifecycle-managed.
- AI usage is observable, but not used as a billing system in this release.
