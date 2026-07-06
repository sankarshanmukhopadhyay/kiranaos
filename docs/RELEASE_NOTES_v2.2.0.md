# KiranaOS v2.2.0 Release Notes

## Release Theme

KiranaOS v2.2.0 is the adoption-ready operational maturity release. It converts the repository from a capable demo into a deployable reference implementation with completed roadmap items, clearer authority boundaries, stronger evidence capture, and documentation suitable for new operators and developers.

## What Changed

### Completed Roadmap Items

- Added provider-aware outbound WhatsApp dispatch for `simulation`, `twilio`, and `meta` modes.
- Added route optimization for delivery assignments using geocoded nearest-neighbour ordering when coordinates exist and deterministic address sorting when they do not.
- Tightened role-based permissions across owner, manager, and staff workflows.

### Security And Control Plane

- Added audit events for sensitive operational mutations.
- Preserved provider message identifiers, dispatch attempts, and failure reasons for outbound confirmations.
- Added production environment template with explicit non-demo settings.
- Added clearer separation between demo mode and production mode.

### Developer Adoption

- Added CI workflow for backend lint/typecheck/test and frontend build.
- Added release archive workflow.
- Added changelog and expanded documentation set.
- Bumped API, backend, and frontend version metadata to `2.2.0`.

## Evidence Produced

The release expands machine-verifiable operational evidence across:

- order status changes;
- order amount changes;
- customer credit adjustments;
- outbound WhatsApp confirmations;
- delivery assignment and delivery status changes;
- route optimization decisions;
- UPI payment reconciliation.

## Upgrade Notes

Fresh installs can run the existing Alembic baseline or allow local SQLite table creation in demo mode. Existing local demo databases should be recreated for v2.2.0 if they were created before the new customer routing, outbound dispatch, and audit fields were added.

## Validation

Recommended release validation:

```bash
make install
make lint
make typecheck
make test
cd frontend && npm install && npm run build
docker compose up --build
make migrate
```

## Known Constraints

- Route optimization is intentionally provider-neutral. It does not call a paid maps API.
- Meta inbound POST payload mapping remains a future provider-specific adapter task; the normalized ingestion endpoint and Meta verification handshake are already present.
- Production deployers must set `KIRANA_DEMO_MODE=false`, `KIRANA_AUTH_REQUIRED=true`, and real secrets before exposing the service.
