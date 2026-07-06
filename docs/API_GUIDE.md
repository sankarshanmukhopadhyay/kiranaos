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
