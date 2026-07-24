---
layout: default
title: Roadmap
parent: Project Governance
nav_order: 2
permalink: /project/roadmap/
source_file: /ROADMAP.md
---

<div class="source-banner">Canonical repository source: <code>ROADMAP.md</code></div>

# KiranaOS Roadmap

KiranaOS follows a commercially sequenced roadmap. Each release must strengthen adoption, daily retention, or monetization evidence without turning AI into an uncontrolled authority layer.

## Completed: Release 1 Commercial Foundation, v2.3.0

Release 1 stabilized the repository for controlled pilots: provider correctness, ingestion safety, review/correction workflow, auth-enabled pilot UI, auditability, tests, and adoption documentation.

## Completed: Release 2 Operations Release, v2.4.0

Release 2 makes KiranaOS useful for daily merchant operations. The release adds product catalog management, substitutions, order item product binding, repeat orders, customer history, staff assignment, order notes, daily operations reporting, feature flags, and AI usage tracking.

### Release 2 acceptance criteria

- A merchant operator can maintain a simple product catalog.
- Ambiguous order items can be corrected and linked to catalog products.
- Approved substitutions can be recorded without rewriting the original customer request.
- Repeat orders can be generated from historical orders.
- Customer history is queryable without manual database inspection.
- Store staff can be assigned to fulfillment tasks.
- AI usage can be recorded and summarized as an operational cost signal.
- The daily report produces operational evidence for pilots.

## Completed: Release 3 Order-to-Cash Release, v2.5.0

Release 3 establishes the monetizable workflow surface: tender-aware payments, order-level reconciliation, controlled refunds and cancellations, daily settlement closure, and accountant-ready exports.

### Release 3 acceptance criteria

- Cash, UPI, and split payments are represented explicitly.
- Payments cannot exceed the outstanding order amount.
- Every order exposes computed paid, refunded, net-paid, and outstanding totals.
- Managers can request refunds, while only owners can approve or reject them.
- Undelivered cancellations produce a reasoned audit event; delivered orders use refunds.
- Daily settlements separate cash, UPI, refunds, and net receipts.
- Only owners can close a settlement.
- CSV and XLSX exports support accountant and POS handoff.
- Financial mutations remain store-scoped and auditable.

## Next: Release 4 Partner and Platform Foundations

Release 4 should focus on controlled integrations and repeatable commercial deployment: plan/quota enforcement, API keys, webhooks, partner-sponsored onboarding, and multi-store portfolio visibility.

## Later

- Distributor-sponsored flows.
- Multi-merchant partner console.
- API keys and webhooks for platform integrations.
- Offline-first workflows.
- Vertical packs for restaurants, pharmacies, bakeries, and cloud kitchens.

## Not planned for core releases

- Autonomous agents with direct write authority.
- Credit scoring.
- Advanced dynamic pricing.
- Marketplace orchestration.
- Distributor monetization before store operations and order-to-cash evidence are stable.

