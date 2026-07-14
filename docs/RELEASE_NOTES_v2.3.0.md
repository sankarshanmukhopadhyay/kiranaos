---
layout: page
title: KiranaOS v2.3.0 Release Notes
permalink: /release-notes-v2.3.0/
---

# KiranaOS v2.3.0 Release Notes

## Release theme

KiranaOS v2.3.0 is the **Release 1 Commercial Foundation Release**. It moves the repository from a broad demo into a pilot-ready merchant workflow foundation. The release does not add billing, distributor workflows, autonomous agents, or advanced payment automation. It stabilizes the product surface needed to run controlled pilots and gather commercial evidence.

## Highlights

- Added provider-correct configuration for OpenAI, Google Vision, and Sarvam dispatch.
- Added review/correction APIs for orders that cannot be safely fulfilled from the initial parse.
- Added duplicate inbound message protection for provider webhook retries.
- Added guarded order lifecycle transitions.
- Added auth-aware frontend API client and operator login/logout flow.
- Added pilot dashboard surfaces for Review Queue, Daily Closing, order inspection, and audit trail viewing.
- Added audit events for review resolution, item correction, customer update, duplicate message handling, and lifecycle changes.
- Added roadmap and pilot readiness documentation.
- Fixed test dependency gap by adding `respx` to the backend dev extras.

## Backend changes

### Configuration

`backend/app/core/config.py` now exposes explicit provider settings:

- `KIRANA_STT_PROVIDER=openai|sarvam|none`
- `KIRANA_OCR_PROVIDER=google_vision|sarvam|none`
- `KIRANA_PARSER_AI_PROVIDER=openai|sarvam|none`
- `KIRANA_SARVAM_API_KEY`
- `KIRANA_SARVAM_STT_MODEL`
- `KIRANA_SARVAM_LLM_MODEL`
- `KIRANA_OPENAI_PARSER_MODEL`
- `KIRANA_PARSE_CONFIDENCE_THRESHOLD`
- `KIRANA_AI_ORDER_QUOTA_PER_DAY`

The health endpoint now returns service version, demo/auth mode, and active provider selections.

### Ingestion and review safety

- Inbound messages now track `parse_failure_reason`.
- Provider webhook retries are deduplicated by `store_id`, `source`, and `external_message_id`.
- Low-confidence item parses are recorded in message evidence and surfaced to operators.
- Unparsed image/voice/text messages continue to fail closed into `needs_review`.
- Manual correction and review resolution endpoints allow operators to convert a review order into a pending order with auditable evidence.

### Order lifecycle governance

Release 1 introduces explicit transition guardrails:

- `needs_review -> pending|cancelled`
- `pending -> packed|cancelled|needs_review`
- `packed -> delivered|cancelled`
- `delivered` and `cancelled` are terminal

Invalid transitions return a client error instead of silently mutating the record.

### Auditability

Audit events now cover:

- duplicate inbound message ignored
- order review resolved
- order items corrected
- customer updated
- order status updated
- order amount updated
- credit adjusted

The audit listing API supports filters by entity, action, and time window.

## Frontend changes

The React dashboard has been simplified around the Release 1 pilot workflow:

- Orders dashboard with lifecycle actions.
- Dedicated Review Queue.
- Order inspection drawer showing raw input, extracted text, notes, items, and audit events.
- Operator login/logout using bearer tokens.
- Daily Closing summary.
- Store name is loaded from the API instead of hardcoded demo copy.

## Documentation changes

Added or updated:

- `ROADMAP.md`
- `docs/PILOT_READINESS.md`
- `docs/RELEASE_NOTES_v2.3.0.md`
- `backend/.env.example`
- `CONTRIBUTING.md`
- `docs/RELEASE_PROCESS.md`
- `docs/AI_PROVIDERS.md`

## Validation

Release validation completed:

```bash
make lint
make typecheck
make test
cd frontend && npm run build
```

Results:

- Backend lint: passed.
- Backend typecheck: passed, 32 source files.
- Backend tests: 57 passed.
- Frontend TypeScript/Vite build: passed.

## Known limitations

- UPI reconciliation remains experimental/beta in Release 1.
- Delivery route optimization remains beta and uses a fallback strategy when geocoded data is absent.
- Billing, subscription enforcement, and distributor-sponsored workflows are intentionally not included.
- Review resolution UI uses a conservative minimal workflow; richer item-edit forms belong in Release 2.
- Release 1 supports controlled pilots, not production SaaS multi-tenancy at scale.
