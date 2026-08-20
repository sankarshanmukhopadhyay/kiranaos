---
layout: default
title: Changelog
parent: Project Governance
nav_order: 4
permalink: /project/changelog/
source_file: /CHANGELOG.md
---

<div class="source-banner">Canonical repository source: <code>CHANGELOG.md</code></div>

# Changelog

## Prototype closeout - August 2026

KiranaOS is closed at a prototype-complete checkpoint. v2.5.0 remains the current implemented Order-to-Cash release; the closeout work makes that implementation coherent, verifiable, and understandable as a durable reference prototype.

### Added

- GitHub Actions CI for backend lint/typecheck/tests, frontend typecheck/build, and documentation integrity.
- `make verify` as the local acceptance gate.
- [Prototype Status]({% link PROJECT_STATUS.md %}) with the implemented/deferred capability boundary.
- [Demo Walkthrough]({% link DEMO_WALKTHROUGH.md %}) covering the full intended journey.

### Changed

- README and documentation home now explain the intended outcome before release history.
- The roadmap is closed at the prototype boundary; former Release 4 work is deferred productization.
- Deployment language no longer implies a production pipeline that the repository does not contain.
- Repository hygiene excludes generated/environment/workstation artifacts and removes tracked `.DS_Store` metadata.
- Release 3 finance formatting/type defects exposed by the restored gate are corrected without changing financial behavior.
- Frontend verification uses dependency-complete TypeScript checking and a Vite build.

### Validation target

`make verify` is the canonical local acceptance command. `.github/workflows/ci.yml` provides independent GitHub evidence for pull requests and `main`.

## Release history

### v2.5.0 - Release 3 Order-to-Cash

Introduced cash, UPI, and split-tender payments; order reconciliation; governed refunds and cancellation; daily settlements; accounting exports; and financial audit evidence.

### v2.4.0 - Release 2 Operations

Introduced catalog management, substitutions, product binding, repeat orders, customer history, staff assignment, order notes, daily operations reporting, feature flags, and AI usage tracking.

### v2.3.0 - Release 1 Commercial Foundation

Stabilized provider behavior, ingestion safety, human review/correction, authentication-enabled pilot UI, auditability, tests, and adoption documentation.

### v2.2.0 - Adoption-Ready Operational Release

Added provider-aware outbound WhatsApp confirmations, delivery routing, role-based authority, and expanded audit evidence.

For detailed historical entries, use the canonical [`CHANGELOG.md`](https://github.com/sankarshanmukhopadhyay/kiranaos/blob/main/CHANGELOG.md) in the repository.
