# Contributing to KiranaOS

KiranaOS is managed as a pilot-safe merchant workflow platform. Contributions should strengthen adoption, operational reliability, evidence, or commercial roadmap clarity.

## Local setup

```bash
make install
make test
make lint
cd frontend && npm run build
```

## Branch naming

Use descriptive branch names:

- `fix/provider-config`
- `feat/review-queue-form`
- `docs/pilot-readiness`
- `test/tenant-isolation`

## Pull request expectations

Each pull request should include:

- Summary of the merchant/operator problem being solved.
- Scope statement and out-of-scope statement.
- Tests added or updated.
- Documentation updated where behavior changes.
- Screenshots for frontend workflow changes.
- Migration notes if database schema changes.

## Architecture rules

- AI output is evidence and proposal, not direct authority for critical state changes.
- Orders requiring ambiguity resolution must be routed through review.
- Payment/refund/credit mutations must be deterministic and auditable.
- Provider configuration must be environment-driven and fail closed.
- Store-scoped data access must remain enforced when auth is enabled.

## Release discipline

Release trains should be substantive. Patch releases should be limited to security, data integrity, or release-blocking defects. Feature expansion should follow `ROADMAP.md`.
