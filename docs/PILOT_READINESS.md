---
layout: default
title: Pilot Readiness Checklist
parent: Guides
nav_order: 4
permalink: /guides/pilot-readiness/
---

# Pilot Readiness Checklist

Use this checklist before running KiranaOS with real merchant data.

## Go/no-go criteria

A pilot is acceptable only when all of the following are true:

- Backend tests pass with `make test`.
- Backend lint passes with `make lint`.
- Frontend build passes with `cd frontend && npm run build`.
- `.env` has production-safe values for auth and webhook secrets.
- A first owner operator has been created and login has been tested.
- The selected STT, OCR, and parser providers are documented in the pilot notes.
- Review fallback is tested with text, image, and voice samples.
- The merchant understands that delivery optimization, UPI reconciliation, and outbound WhatsApp confirmations are beta/experimental surfaces in Release 1.

## Required pilot setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `KIRANA_AUTH_REQUIRED=true` for any real pilot.
3. Replace `KIRANA_JWT_SECRET` and `KIRANA_WHATSAPP_VERIFY_TOKEN`.
4. Select provider modes:
   - `KIRANA_STT_PROVIDER=openai|sarvam|none`
   - `KIRANA_OCR_PROVIDER=google_vision|sarvam|none`
   - `KIRANA_PARSER_AI_PROVIDER=openai|sarvam|none`
5. Create the first operator using `POST /api/operators` before enabling additional users.
6. Run a smoke test:
   - `GET /api/health`
   - `POST /api/ingest/messages`
   - `GET /api/orders`
   - `POST /api/orders/{id}/review/resolve` for a review order
   - `GET /api/audit/events?entity_type=order&entity_id={id}`

## Pilot evidence to collect

- Orders ingested per merchant per day.
- Percentage of orders requiring review.
- Item correction rate.
- Duplicate webhook event count.
- Time from inbound message to pending order.
- Manual intervention reasons.
- Operator-reported fit for daily workflow.

## Data handling

Release 1 stores raw inbound text, extracted text, parser results, customer metadata, order state, and audit events. Media URLs are validated to reduce SSRF risk, but operators should still treat inbound media as customer data. Set retention expectations before the pilot begins.
