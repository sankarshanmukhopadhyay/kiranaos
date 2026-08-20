---
layout: home
title: Home
nav_order: 1
permalink: /
---

# KiranaOS Documentation

KiranaOS is a WhatsApp-native merchant operations prototype for small businesses that receive orders through conversational channels. It demonstrates how unstructured text, image, and voice-style orders can become structured merchant workflows without making AI an uncontrolled authority layer.

> **Project state:** prototype complete for the current objective, not production ready. The codebase is intended to be demonstrable, inspectable, and suitable as a starting point for a controlled pilot or future productization effort.

[Run the demo walkthrough]({% link DEMO_WALKTHROUGH.md %}){: .btn .btn-primary }
[Review prototype status]({% link PROJECT_STATUS.md %}){: .btn }

## What the prototype demonstrates

The core journey is customer message → normalized ingestion → interpretation/review → structured order → store operations → payment/credit → settlement → accounting and audit evidence.

AI-assisted interpretation is deliberately separated from operational authority. Low-confidence input can be routed to human review, while material merchant and financial mutations remain governed by deterministic workflows, role scope, and audit events.

## Guided learning path

1. **See the intended outcome:** [Demo Walkthrough]({% link DEMO_WALKTHROUGH.md %}).
2. **Understand the boundary:** [Prototype Status]({% link PROJECT_STATUS.md %}) and [Pilot Readiness]({% link PILOT_READINESS.md %}).
3. **Understand the system:** [Architecture]({% link ARCHITECTURE.md %}), [API Guide]({% link API_GUIDE.md %}), and [Security Model]({% link SECURITY_MODEL.md %}).
4. **Operate the workflow:** [Daily Operations]({% link OPERATIONS.md %}) and [Order-to-Cash]({% link ORDER_TO_CASH.md %}).
5. **Assure the repository:** [Testing]({% link TESTING.md %}), [Release Process]({% link RELEASE_PROCESS.md %}), and [Security Policy]({% link project/security.md %}).
6. **Understand future scope:** [Roadmap]({% link project/roadmap.md %}) and [Changelog]({% link project/changelog.md %}).

## Completed capability sequence

| Release | Outcome | Evidence surface |
|---|---|---|
| Release 1 | Commercial foundation | Safe ingestion, review, authentication, auditability |
| Release 2 | Store operations | Catalog, fulfilment, assignments, daily reporting |
| Release 3 / v2.5.0 | Order-to-Cash | Payments, refunds, settlements, accounting exports |
| Prototype closeout | Coherent demonstrator | CI, one-command verification, demo walkthrough, explicit production boundary |

## Verification

Run the repository acceptance gate locally with:

```bash
make verify
```

GitHub Actions independently runs backend tests/lint/typecheck, frontend TypeScript typecheck/build, and documentation validation.
