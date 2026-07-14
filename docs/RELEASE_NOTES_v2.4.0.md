---
layout: page
title: KiranaOS v2.4.0 Release Notes
permalink: /release-notes-v2.4.0/
---

# KiranaOS v2.4.0 Release Notes

**Release name:** Release 2 Operations Release  
**Release type:** Minor feature and maturity release  
**Primary goal:** Turn the Release 1 commercial foundation into a daily merchant operations workflow.

KiranaOS v2.4.0 adds the operational surfaces needed for real pilots: catalog management, substitutions, order-item product binding, repeat orders, customer history, staff assignment, daily operations reporting, feature flags, and AI usage tracking. It does not add billing, distributor workflows, autonomous agents, or advanced payment automation.

## Release posture

Release 2 keeps the core governance posture from Release 1. AI remains an intake and interpretation layer. Human operators and deterministic workflow states remain responsible for order correction, substitutions, fulfillment assignment, and operational decisions.

## Major additions

### Product catalog

Release 2 introduces a store-scoped product catalog with SKU, canonical name, category, unit, price, stock quantity, status, and notes. Catalog changes are audited.

New endpoints include:

- `GET /api/catalog/products`
- `POST /api/catalog/products`
- `GET /api/catalog/products/{product_id}`
- `PATCH /api/catalog/products/{product_id}`

### Product substitutions

Operators can record acceptable substitutions between catalog products. This creates a structured fulfillment signal without overwriting the original customer request.

New endpoints include:

- `POST /api/catalog/products/{product_id}/substitutions`
- `GET /api/catalog/products/{product_id}/substitutions`

### Order item product binding

Order item corrections now support optional `product_id`, `substitution_for_item_id`, and item notes. This lets the review workflow connect messy customer requests to operational catalog records.

### Repeat orders

Repeat orders can be generated from previous orders for the same customer. This supports high-frequency kirana and restaurant workflows where customers often ask for “same as last time.”

New endpoint:

- `POST /api/orders/{order_id}/repeat`

### Customer history

Customer history now provides recent orders, lifetime order count, lifetime amount, and top ordered items.

New endpoint:

- `GET /api/customers/{customer_id}/history`

### Staff assignment

Store operators can assign orders to staff members for fulfillment roles such as packing, delivery preparation, or counter handling. Assignments have lifecycle states and audit events.

New endpoints include:

- `POST /api/orders/{order_id}/staff-assignments`
- `GET /api/staff-assignments`
- `PATCH /api/staff-assignments/{assignment_id}`

### Order notes

Order-level notes can now be updated separately from item correction and status changes.

New endpoint:

- `PATCH /api/orders/{order_id}/notes`

### AI usage tracking

Release 2 adds AI usage event capture so pilots can measure provider usage, estimated units, estimated cost, success, and failure reason. This is not billing. It is operational evidence for future pricing and cost-control design.

New endpoints include:

- `POST /api/operations/ai-usage`
- `GET /api/operations/ai-usage`
- `GET /api/operations/ai-usage/summary`

### Daily operations report

A new operations report combines order volumes, review burden, delivery state, credit totals, average order value, top items, and AI usage signals.

New endpoint:

- `GET /api/operations/daily-report`

### Feature flags

Release 2 introduces feature flags for operations surfaces:

- `KIRANA_CATALOG_ENABLED`
- `KIRANA_STAFF_ASSIGNMENT_ENABLED`
- `KIRANA_REPEAT_ORDERS_ENABLED`
- `KIRANA_AI_USAGE_TRACKING_ENABLED`
- `KIRANA_PAYMENTS_ENABLED`
- `KIRANA_DELIVERY_ENABLED`

New endpoint:

- `GET /api/features`

## Schema and migration changes

Added:

- `products`
- `product_substitutions`
- `staff_assignments`
- `ai_usage_events`

Extended:

- `order_items.product_id`
- `order_items.substitution_for_item_id`
- `order_items.notes`

Migration:

- `backend/alembic/versions/20260714_0100_release2_operations.py`

## Documentation updates

Release 2 refreshes the documentation set and makes the documentation available for GitHub Pages/Jekyll rendering under `docs/`.

Updated or added:

- `docs/index.md`
- `docs/_config.yml`
- `docs/RELEASE_NOTES_v2.4.0.md`
- `docs/OPERATIONS_RELEASE.md`
- `docs/JEKYLL_GITHUB_PAGES.md`
- `docs/API_GUIDE.md`
- `docs/OPERATIONS.md`
- `docs/TESTING.md`
- `ROADMAP.md`
- `CHANGELOG.md`

## Validation

Validated successfully:

```bash
make test
make lint
make typecheck
cd frontend && npm run build
```

Results:

- Backend tests: 63 passed.
- Backend lint: passed.
- Backend typecheck: passed, 32 source files.
- Frontend TypeScript/Vite build: passed.

## Explicitly out of scope

- Billing and subscription enforcement.
- Distributor-sponsored workflows.
- Autonomous agents or MCP orchestration.
- Advanced payment automation.
- Credit scoring.
- Marketplace/distributor dashboards.

## Upgrade notes

1. Run Alembic migrations before using Release 2 against an existing database.
2. Review `.env.example` for new feature flags.
3. Keep catalog and staff assignment enabled only for pilots ready to use those workflows.
4. Treat AI usage tracking as an internal evidence tool, not customer billing.
