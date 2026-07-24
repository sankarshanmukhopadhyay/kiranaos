---
layout: default
title: Changelog
parent: Project Governance
nav_order: 3
permalink: /project/changelog/
source_file: /CHANGELOG.md
---

<div class="source-banner">Canonical repository source: <code>CHANGELOG.md</code></div>

# Changelog

## v2.5.0 - Release 3 Order-to-Cash Release

Release 3 adds controlled financial execution to the KiranaOS workflow. It introduces cash, UPI, and split-tender payments; order reconciliation summaries; manager-requested and owner-approved refunds; financial cancellation controls; daily settlement generation and closure; and CSV/XLSX accounting exports.

### Added

- Tender-aware payment fields and manual payment endpoint.
- Order payment summaries with paid, refunded, net-paid, and outstanding totals.
- Refund request and owner decision workflow.
- Financial cancellation endpoint for undelivered orders.
- Daily settlement model, generation, listing, and owner-only closure.
- CSV and XLSX accountant/POS export endpoints.
- Release 3 Alembic migration and order-to-cash operating guide.
- Audit actions for payment, refund, cancellation, settlement, and export controls.

### Changed

- Bumped backend, frontend, and API metadata to `2.5.0`.
- UPI webhook reconciliation now records UPI tender allocation explicitly.
- Payment status supports partial and full refund states.
- Roadmap now marks Release 3 complete and positions Release 4 as the partner/platform foundation.

### Validation

- Backend source compilation passed.
- Core API and parser suite: 57 tests passed, including all new Release 3 tests.
- CSV and XLSX export generation validated.


## v2.4.0 - Release 2 Operations Release

Release 2 moves KiranaOS from a pilot-safe order capture foundation into a daily merchant operations workflow. It adds catalog management, product substitutions, product binding on order items, repeat orders, customer history, staff assignment, daily operations reporting, feature flags, and AI usage tracking. It keeps the Release 1 safety posture intact: AI remains an intake/proposal layer, and operational authority stays with deterministic workflows and human review.

### Added

- Product catalog models, schemas, API endpoints, and audit events.
- Product substitution records for operator-approved alternative fulfillment.
- Optional product binding and item notes on order item corrections.
- Repeat-order endpoint for fast reorder creation from prior customer orders.
- Customer history endpoint with recent orders, lifetime totals, and top items.
- Staff assignment lifecycle for fulfillment work allocation.
- Order notes endpoint for operational delivery/packing instructions.
- Feature flag endpoint and environment flags for catalog, staff assignment, repeat orders, AI usage tracking, delivery, and payments.
- AI usage event recording and daily summary endpoints.
- Operations daily report endpoint combining order, review, credit, item, and AI usage metrics.
- Alembic migration `20260714_0100_release2_operations.py`.
- Jekyll/GitHub Pages documentation site under `docs/`.
- Release 2 adoption, operations, API, and testing documentation refresh.

### Changed

- Bumped backend, frontend, and API metadata to `2.4.0`.
- Expanded daily closing output with pending, packed, and manual intervention metrics.
- Extended frontend typed API client to cover Release 2 operations endpoints.
- Updated `.env.example` with Release 2 feature flags.
- Updated roadmap to make Release 2 the current completed operations milestone and Release 3 the next order-to-cash milestone.

### Validation

- `make test`: 63 backend tests passed.
- `make lint`: passed.
- `make typecheck`: passed, 32 backend source files.
- `cd frontend && npm run build`: passed.

## v2.3.0 - Release 1 Commercial Foundation

Release 1 stabilizes KiranaOS for controlled merchant pilots. It is intentionally scoped to repo health, provider correctness, ingestion safety, review/correction workflow, auth-enabled pilot UI, auditability, tests, and adoption documentation.

### Added

- Provider settings for `KIRANA_STT_PROVIDER`, `KIRANA_OCR_PROVIDER`, and `KIRANA_PARSER_AI_PROVIDER` with explicit OpenAI, Google Vision, Sarvam, and `none` modes.
- Health endpoint provider diagnostics and version metadata.
- Duplicate inbound message protection using `store_id`, `source`, and `external_message_id`.
- `parse_failure_reason` evidence on inbound messages.
- Order item correction endpoint.
- Review resolution endpoint.
- Daily closing summary endpoint.
- Customer update endpoint.
- Expanded audit events and audit filters.
- Auth-aware frontend API client and operator login/logout UI.
- Review Queue, Daily Closing, and order inspection drawer in the frontend.
- `ROADMAP.md`, `docs/PILOT_READINESS.md`, and `docs/RELEASE_NOTES_v2.3.0.md`.
- GitHub Actions CI workflow for backend lint/tests and frontend build.

### Changed

- Bumped backend, frontend, and API metadata to `2.3.0`.
- Reframed README around the Release 1 commercial foundation and controlled pilot workflow.
- Updated `.env.example` to match the provider model and pilot security posture.
- Routed voice transcription through a provider-dispatched facade.
- Routed parser fallback through a provider-dispatched AI facade.
- Enforced guarded order status transitions.

### Fixed

- Added missing `respx` dev dependency required by Sarvam adapter tests.
- Removed README overclaims about missing release artifacts by adding current release notes and CI workflow.
- Ensured frontend store display is loaded from the API instead of hardcoded demo copy.

### Validation

- `make lint`: passed.
- `make typecheck`: passed, 32 source files.
- `make test`: 57 tests passed.
- `cd frontend && npm run build`: passed.

## v2.2.0 - Adoption-Ready Operational Release

- Added provider-aware outbound WhatsApp confirmations for simulation, Twilio, and Meta.
- Added deterministic delivery route optimization with geocoded nearest-neighbour routing and address-sort fallback.
- Added role-based authority across owner, manager, and staff workflows.
- Added audit events for order, credit, outbound, delivery, route, and payment mutations.
- Bumped backend, frontend, and API metadata to `2.2.0`.

