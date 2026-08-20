---
layout: default
title: Project Overview
parent: Project Governance
nav_order: 1
permalink: /project/overview/
source_file: /README.md
---

<div class="source-banner">Canonical repository source: <code>README.md</code></div>

# KiranaOS

**WhatsApp-native order capture and governed daily merchant operations for kirana stores and small businesses.**

KiranaOS demonstrates a simple product thesis: customers should be able to keep ordering through familiar conversational channels while the merchant gets a structured operational system behind those messages.

A customer can send freeform text, a photo of a handwritten list, or a voice note. KiranaOS normalizes the input, proposes structured order data, routes uncertain interpretation to human review, and then carries the resulting order through merchant operations, payment/credit, settlement, accounting handoff, and audit evidence.

> **Project state:** prototype complete for the current objective. KiranaOS is not production ready and is not presented as a hardened commercial deployment.

The current codebase is intended to be understandable, runnable, demonstrable, and useful as a starting point for a controlled pilot or future productization effort.

## What KiranaOS proves

The prototype brings five ideas together:

1. **No customer-side app or workflow change is required.** Conversational inputs enter one normalized ingestion boundary.
2. **AI is assistive, not authoritative.** Low-confidence parsing can require explicit human review before fulfillment.
3. **Merchant operations become structured.** Orders, customers, udhaari, catalog products, substitutions, staff work, delivery, and notes are represented explicitly.
4. **Order-to-cash is governable.** Payments, refunds, cancellations, settlements, and accounting exports have scoped authority and audit evidence.
5. **The intended system can be inspected end-to-end.** Frontend, API, simulation mode, tests, documentation, and CI exist in one repository.

The shortest way to understand the intended outcome is the [Demo Walkthrough]({% link DEMO_WALKTHROUGH.md %}). The formal project boundary is in [Prototype Status]({% link PROJECT_STATUS.md %}).

## Quick start

```bash
git clone https://github.com/sankarshanmukhopadhyay/kiranaos.git
cd kiranaos
make dev
```

Open **http://localhost:5173**. The interactive API documentation is at **http://localhost:8000/docs**.

Use **Simulate WA order** in the application sidebar to exercise the local ingestion and merchant workflow without external provider credentials.

### Without Docker

```bash
make install
make dev-api
make dev-frontend
make seed
```

## One-command verification

```bash
make verify
```

The acceptance gate runs backend tests, backend lint/type checking, frontend lint/build, and documentation validation. The same gates are represented in `.github/workflows/ci.yml`.

## End-to-end operating model

```text
Customer message
      │
      ▼
Normalized ingestion
      │
      ▼
Interpretation / confidence
      │
      ├── uncertain ──► human review ──┐
      │                                │
      └──────────── valid ─────────────┘
                       │
                       ▼
                 Structured order
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
      customer      fulfilment    delivery
      context          work          work
         └─────────────┼─────────────┘
                       ▼
                payment / credit
                       │
                       ▼
                   settlement
                       │
                       ▼
             accounting + audit
```

The architectural boundary is deliberate: **message interpretation does not itself grant operational authority**. Parsing proposes structure. Merchant workflows determine what becomes actionable.

## Implemented capability surface

| Area | Prototype capability |
|---|---|
| Ingestion | Normalized ingest API, Twilio WhatsApp adapter, Meta verification route, duplicate protection |
| Interpretation | Deterministic text parser, provider-dispatched OCR/STT/LLM adapters, safe fallback |
| Human review | Review queue, item correction, explicit review resolution |
| Orders | Guarded lifecycle transitions, amount/udhaari state, repeat orders |
| Customers | History, dormant-customer visibility, udhaari ledger |
| Catalog | Products, bindings, operator-approved substitutions |
| Fulfillment | Staff assignment, notes, delivery assignment, route ordering |
| Payments | Cash, UPI, split tender, order reconciliation summaries |
| Exceptions | Controlled refund and cancellation workflows |
| Settlement | Daily settlement generation and owner closure |
| Accounting | CSV and XLSX export |
| Governance | Store scope, optional JWT authentication, role permissions, audit events |
| Assurance | Backend tests/lint/typecheck, frontend lint/build, docs validation, CI |

## Repository structure

```text
kiranaos/
├── backend/                 FastAPI application, SQLAlchemy models, services, tests, Alembic
├── frontend/                React/Vite merchant dashboard
├── docs/                    Architecture, operations, security, demo and project documentation
├── demos/                   Recorded explanatory/working demo assets
├── scripts/                 Documentation validation utilities
├── .github/workflows/       CI and GitHub Pages publication
├── docker-compose.yml       Local full-stack environment
├── Makefile                 Development and verification commands
├── ROADMAP.md               Closed prototype roadmap and deferred productization work
└── SECURITY.md              Security posture and deployment boundary
```

## Configuration and deployment boundary

Configuration uses the `KIRANA_` prefix. Copy `backend/.env.example` to `backend/.env` for local overrides. External providers are optional for understanding the prototype: text orders and the local simulation path are enough to exercise the core architecture.

Docker Compose is the recommended local demonstration environment. Railway and Vercel configuration files remain as deployment examples, but the repository does **not** claim an automated production deployment pipeline.

Taking KiranaOS beyond this checkpoint would require explicit work on production tenancy, secrets, recovery, observability, queue/retry behavior, scale/concurrency testing, payment/compliance integration, and other items listed in [Roadmap]({% link project/roadmap.md %}).

## Project disposition

Releases 1–3 established the commercial foundation, daily operations, and order-to-cash workflow. The August 2026 closeout completes the repository as a coherent reference prototype by adding an explicit acceptance gate, end-to-end walkthrough, production boundary, and closed roadmap.

Further feature development should be driven by a concrete pilot or product requirement rather than by an open-ended backlog.

## License

MIT © 2026 KiranaOS Contributors
