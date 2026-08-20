---
layout: default
title: Roadmap
parent: Project Governance
nav_order: 3
permalink: /project/roadmap/
source_file: /ROADMAP.md
---

<div class="source-banner">Canonical repository source: <code>ROADMAP.md</code></div>

# KiranaOS Roadmap

KiranaOS has reached the intended **prototype-complete** state for the current project. The repository now demonstrates the end-to-end merchant operating model from conversational order capture through review, store operations, payment, settlement, accounting handoff, and audit evidence.

Further work is intentionally demand-driven rather than roadmap-driven. New implementation should begin only when there is a concrete pilot, adoption, integration, or production requirement.

## Completed: Release 1 Commercial Foundation, v2.3.0

Release 1 stabilized the repository for controlled pilots: provider correctness, ingestion safety, review/correction workflow, auth-enabled pilot UI, auditability, tests, and adoption documentation.

## Completed: Release 2 Operations Release, v2.4.0

Release 2 made KiranaOS useful as a daily merchant operations demonstrator: product catalog management, substitutions, product binding, repeat orders, customer history, staff assignment, order notes, daily operations reporting, feature flags, and AI usage tracking.

## Completed: Release 3 Order-to-Cash Release, v2.5.0

Release 3 established the monetizable workflow surface: cash, UPI, and split payments; order reconciliation; controlled refunds and cancellations; daily settlement closure; and accountant-ready CSV/XLSX exports.

## Completed: Prototype closeout, August 2026

The closeout checkpoint makes the repository meaningful as a durable reference implementation rather than an unfinished feature sequence.

Acceptance criteria:

- The intended outcome is explained through an end-to-end demo walkthrough.
- Implemented capabilities and deferred production requirements are explicitly separated.
- Backend tests, linting, and type checking are represented in CI.
- Frontend linting and build are represented in CI.
- Documentation integrity is represented in CI and GitHub Pages publication remains supported.
- `make verify` provides one local acceptance gate.
- Repository hygiene excludes generated, environment, and workstation artifacts.
- No future platform or production feature is implied to be required for the prototype to be considered complete.

## Deferred until there is a concrete need

The former “Release 4 Partner and Platform Foundations” is no longer an active release commitment. The following capabilities are deferred:

- plan/quota enforcement and billing;
- API keys and external partner webhooks;
- partner-sponsored onboarding;
- multi-store portfolio/partner console;
- distributor-sponsored flows;
- offline-first synchronization;
- vertical-specific packs;
- production infrastructure hardening, SLOs, observability, backup/recovery, and scale testing;
- formal payment/compliance integrations.

These items are productization work, not missing proof-of-concept functionality.

## Explicitly not planned without a new project mandate

- autonomous agents with direct write authority;
- credit scoring;
- advanced dynamic pricing;
- marketplace orchestration;
- distributor monetization before a validated merchant adoption case exists.

See [Prototype Status]({% link PROJECT_STATUS.md %}) for the formal boundary and [Demo Walkthrough]({% link DEMO_WALKTHROUGH.md %}) for the shortest path through the intended outcome.
