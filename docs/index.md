---
layout: home
title: Home
nav_order: 1
permalink: /
---

# KiranaOS Documentation

KiranaOS is a WhatsApp-native merchant operating system for small businesses that receive orders through chat, voice, and images. The documentation treats each workflow as an auditable control surface: who may act, what scope applies, what evidence is produced, and how authority can be reviewed or revoked.

## Current release

**v2.5.0, Release 3 Order-to-Cash**, adds tender-aware cash, UPI, and split payments; controlled refunds and cancellations; closeable daily settlements; and accountant-ready CSV/XLSX exports.

[Start the adoption path]({% link ADOPTION_GUIDE.md %}){: .btn .btn-primary }
[Review Order-to-Cash]({% link ORDER_TO_CASH.md %}){: .btn }

## Guided learning path

1. **Evaluate:** [Adoption Guide]({% link ADOPTION_GUIDE.md %}) and [Pilot Readiness]({% link PILOT_READINESS.md %}).
2. **Understand:** [Architecture]({% link ARCHITECTURE.md %}), [API Guide]({% link API_GUIDE.md %}), and [Security Model]({% link SECURITY_MODEL.md %}).
3. **Operate:** [Daily Operations]({% link OPERATIONS.md %}) and [Order-to-Cash]({% link ORDER_TO_CASH.md %}).
4. **Assure:** [Testing]({% link TESTING.md %}), [Release Process]({% link RELEASE_PROCESS.md %}), and [Security Policy]({% link project/security.md %}).
5. **Track maturity:** [Roadmap]({% link project/roadmap.md %}) and [Changelog]({% link project/changelog.md %}).

## Release sequence

| Release | Outcome | Evidence surface |
|---|---|---|
| Release 1 | Commercial foundation | Safe ingestion, review, authentication, auditability |
| Release 2 | Store operations | Catalog, fulfilment, assignments, daily reporting |
| Release 3 | Order-to-Cash | Payments, refunds, settlements, accounting exports |
