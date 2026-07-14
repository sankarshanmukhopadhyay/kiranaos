---
layout: page
title: API Guide
permalink: /api-guide/
---

# API Guide

All endpoints are prefixed with `/api`. The interactive OpenAPI documentation is available at `/docs`.

## Ingest A Text Order

```bash
curl -X POST http://localhost:8000/api/ingest/messages \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919999999999","customer_name":"Priya","text":"2 kg atta, 1 l oil"}'
```

## Update Order Status

```bash
curl -X PATCH http://localhost:8000/api/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"packed"}'
```

## Send Outbound Confirmation

```bash
curl -X POST http://localhost:8000/api/orders/1/confirmations \
  -H "Content-Type: application/json" \
  -d '{"body":"Your order is packed and will be delivered soon."}'
```

The response includes provider, status, provider message id, failure reason, and dispatch attempts.

## Optimize Delivery Route

```bash
curl -X POST http://localhost:8000/api/delivery/routes/optimize \
  -H "Content-Type: application/json" \
  -d '{"agent_id":1}'
```

The API uses geocoded nearest-neighbour ordering when all stops have coordinates. Otherwise it uses deterministic building/address ordering.

## Inspect Audit Events

```bash
curl http://localhost:8000/api/audit/events
```

Audit events are store-scoped and record the action, entity, actor, timestamp, and JSON evidence payload.

## Release 2 Operations API

Release 2 adds operational endpoints that are intentionally separate from the original ingestion and review workflow. These endpoints support daily merchant operations without giving AI direct authority over the system of record.

### Feature flags

```http
GET /api/features
```

Returns enabled operational capabilities for the current deployment:

- `catalog_enabled`
- `staff_assignment_enabled`
- `repeat_orders_enabled`
- `ai_usage_tracking_enabled`
- `payments_enabled`
- `delivery_enabled`

### Catalog products

```http
GET /api/catalog/products
POST /api/catalog/products
GET /api/catalog/products/{product_id}
PATCH /api/catalog/products/{product_id}
```

Product records are store-scoped. `sku` must be unique within a store.

Example create payload:

```json
{
  "sku": "ATTA-5KG",
  "name": "Atta 5kg",
  "canonical_name": "Atta",
  "category": "staples",
  "unit": "bag",
  "price": 260,
  "stock_quantity": 12,
  "status": "active"
}
```

### Product substitutions

```http
POST /api/catalog/products/{product_id}/substitutions
GET /api/catalog/products/{product_id}/substitutions
```

Example payload:

```json
{
  "substitute_product_id": 2,
  "reason": "larger pack available"
}
```

### Order notes and repeat orders

```http
PATCH /api/orders/{order_id}/notes
POST /api/orders/{order_id}/repeat
```

Repeat orders create a new order from a previous order's items. They do not mutate the source order.

### Staff assignments

```http
POST /api/orders/{order_id}/staff-assignments
GET /api/staff-assignments
PATCH /api/staff-assignments/{assignment_id}
```

Assignment statuses:

- `assigned`
- `accepted`
- `completed`
- `reassigned`
- `cancelled`

### Customer history

```http
GET /api/customers/{customer_id}/history
```

Returns:

- customer profile
- recent orders
- lifetime order count
- lifetime amount due
- top ordered items

### AI usage tracking

```http
POST /api/operations/ai-usage
GET /api/operations/ai-usage
GET /api/operations/ai-usage/summary
```

Example payload:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "purpose": "parse",
  "order_id": 123,
  "estimated_units": 42,
  "estimated_cost": 0.002,
  "success": true
}
```

### Daily operations report

```http
GET /api/operations/daily-report
```

Returns daily order totals, review burden, pending/packed state, credit totals, average order value, top items, and AI usage signals.
