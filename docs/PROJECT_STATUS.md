---
layout: default
title: Prototype Status
parent: Project Governance
nav_order: 2
permalink: /project/status/
---

# KiranaOS Prototype Status

KiranaOS is **prototype complete** for its current objective: demonstrate that a small merchant can keep receiving unstructured customer orders through WhatsApp-style channels while the merchant side gains a structured, reviewable, auditable operating workflow from order capture through settlement.

The repository is intentionally **not production ready**. The current checkpoint is a coherent reference implementation and pilot demonstrator, not a commitment that the software is ready for unsupervised commercial deployment.

## Intended outcome

The prototype is designed to prove five things together:

1. **No customer-side behavior change is required.** Text, image, and voice-style inputs can enter one normalized ingestion pipeline.
2. **AI remains assistive rather than authoritative.** Low-confidence or failed parsing routes to human review instead of silently executing merchant actions.
3. **Merchant operations become structured.** Orders, catalog bindings, substitutions, customer history, staff assignments, delivery, credit, and notes are represented explicitly.
4. **Order-to-cash is governable.** Payments, refunds, cancellations, settlements, and accounting exports have scoped authority and audit evidence.
5. **The system can be inspected as a whole.** A frontend, API, tests, documentation, deterministic simulation path, and CI gate make the intended operating model understandable without external services.

## Capability matrix

| Area | Prototype status | Evidence |
|---|---|---|
| Message ingestion | Complete | Normalized ingest API, Twilio adapter, Meta verification route, duplicate protection |
| Text parsing | Complete | Deterministic parser plus optional AI fallback |
| Voice and image adapters | Demonstrated | Provider abstractions with safe fallback when credentials are absent |
| Human review | Complete | Review queue, item correction, explicit review resolution |
| Order lifecycle | Complete | Guarded status transitions and auditable mutations |
| Customer and udhaari | Complete | Customer records, ledger, dormant-customer visibility |
| Catalog and substitutions | Complete | Product binding and operator-approved substitution records |
| Fulfilment | Complete | Staff assignment, notes, delivery assignment and route ordering |
| Payments | Complete for prototype | Cash, UPI, split tender, reconciliation summaries |
| Refunds and cancellations | Complete for prototype | Role-controlled approval and evidence |
| Daily settlement | Complete for prototype | Settlement generation and owner closure |
| Accounting handoff | Complete for prototype | CSV/XLSX export |
| Multi-store scope | Demonstrated | Store-scoped operational models and service queries |
| Authentication and roles | Demonstrated | Optional JWT enforcement and owner/manager/staff permissions |
| Observability | Basic | Health diagnostics, audit events, AI usage tracking |
| Automated verification | Complete for prototype | Backend tests/lint/typecheck, frontend lint/build, docs validation in CI |
| Deployment | Demonstrated only | Docker Compose, Railway/Vercel configuration examples |

## Explicitly deferred

The following work is deliberately outside the prototype-complete boundary:

- production-grade tenancy isolation and infrastructure hardening;
- managed secrets, key rotation, SSO, recovery, and enterprise identity integration;
- production webhook retry, queueing, dead-letter, rate-limit, and idempotency infrastructure beyond current controls;
- formal SLOs, distributed tracing, alerting, backup/restore drills, and disaster recovery;
- production payment-provider certification or regulatory/compliance assurance;
- high-scale load, concurrency, chaos, and failure-injection testing;
- offline-first synchronization;
- partner API keys, external webhooks, quotas, billing, sponsored onboarding, and portfolio consoles;
- distributor or marketplace orchestration;
- autonomous agents with direct write authority.

These are not defects in the current checkpoint. They are the next maturity layer if KiranaOS is ever taken toward production.

## Acceptance gate

A repository state is considered consistent with this checkpoint when:

```bash
make verify
```

passes. The command covers backend tests, backend linting and type checking, frontend lint/build, and documentation integrity. The same checks are represented in `.github/workflows/ci.yml`.

## How to evaluate the prototype

Use the [Demo Walkthrough]({% link DEMO_WALKTHROUGH.md %}) to exercise the intended journey from inbound order to review, fulfilment, payment, settlement, and audit evidence. Use the [Architecture]({% link ARCHITECTURE.md %}) and [Security Model]({% link SECURITY_MODEL.md %}) for the authority and trust boundaries behind that journey.

## Project disposition

The current codebase should now be treated as a **reference prototype that can be demonstrated, studied, forked, or used as the starting point for a controlled pilot**. Further feature development should begin only when there is a concrete adoption hypothesis or production requirement to justify it.
