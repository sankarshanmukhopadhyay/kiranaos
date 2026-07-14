---
layout: page
title: Adoption Guide
permalink: /adoption-guide/
---

# Adoption Guide

This guide is for a developer or operator evaluating KiranaOS for a real kirana workflow.

## 30-Minute Evaluation Path

1. Start the stack:

```bash
make dev
```

2. Open the frontend at `http://localhost:5173`.
3. Open the API docs at `http://localhost:8000/docs`.
4. Click **Simulate WA Message** in the frontend.
5. Move an order from pending to packed to delivered.
6. Add udhaari and record settlement.
7. Create a delivery agent, assign an order, and inspect the route.

## Production Readiness Checklist

| Area | Required action |
|---|---|
| Runtime mode | Set `KIRANA_DEMO_MODE=false` |
| Authentication | Set `KIRANA_AUTH_REQUIRED=true` |
| JWT signing | Replace `KIRANA_JWT_SECRET` |
| Database | Use Postgres and run `make migrate` |
| CORS | Set an exact `KIRANA_FRONTEND_ORIGIN` |
| WhatsApp inbound | Configure provider webhook secrets |
| WhatsApp outbound | Choose `simulation`, `twilio`, or `meta` |
| Payments | Set `KIRANA_UPI_WEBHOOK_SECRET` |
| Operators | Bootstrap owner, then create manager/staff accounts |

## Operating Model

KiranaOS treats store operations as executable governance. Authority is scoped by store, delegated through operator roles, and evidenced through database records.

| Role | Intended use |
|---|---|
| `owner` | Store and operator governance |
| `manager` | Amount, credit, delivery, payment, and audit workflows |
| `staff` | Day-to-day order and route execution |

## Deployment Baseline

Use `.env.production.example` as the production starting point. Do not expose a deployment using the demo defaults.
