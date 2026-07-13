# Changelog

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
