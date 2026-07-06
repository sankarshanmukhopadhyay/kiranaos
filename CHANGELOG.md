# Changelog

## v2.2.0 - Adoption-Ready Operational Release

- Completed the maturity roadmap with provider-aware outbound WhatsApp dispatch, deterministic delivery route optimization, and consistent role-based access control.
- Added Twilio, Meta Cloud API, and simulation outbound confirmation modes.
- Added audit events for order, credit, outbound confirmation, delivery, route optimization, and payment reconciliation mutations.
- Added customer address and coordinate fields to support route planning.
- Added route optimization API with geocoded nearest-neighbour routing and deterministic address-sort fallback.
- Added production environment template, CI workflows, release archive workflow, and expanded documentation.
- Bumped backend, frontend, and API metadata to `2.2.0`.

## v2.1.1 - Security Hardening Release

- Hardened JWT verification, webhook validation, CORS posture, startup secret validation, SSRF protection, and tenant-scoped duplicate detection.

## v2.1.0 - Operational Roadmap Release

- Added voice note fallback, outbound confirmation records, delivery assignment, UPI reconciliation, Alembic baseline, multi-store scope, and operator authentication.
