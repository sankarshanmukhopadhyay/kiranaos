---
layout: default
title: Testing Guide
parent: Technical Reference
nav_order: 4
permalink: /reference/testing/
---

# Testing Guide

## Backend

```bash
make lint
make typecheck
make test
```

Backend tests use SQLite and do not require WhatsApp, Google Vision, OpenAI, or UPI credentials.

## Frontend

```bash
cd frontend
npm install
npm run build
```

## Manual Release Checks

- Text message ingestion creates pending orders.
- Image or voice without configured adapters creates `needs_review` orders.
- Order status changes create audit events.
- Credit adjustments create ledger and audit records.
- Outbound confirmation records provider status and failure details.
- Route optimization updates route order deterministically.
- Production startup rejects placeholder secrets.

## Release 2 test coverage

Release 2 adds integration tests for:

- Feature flag discovery.
- Catalog product create/update/list flows.
- Product substitutions.
- Order item correction with catalog product binding and item notes.
- Repeat orders.
- Customer history.
- Staff assignment lifecycle.
- Order notes.
- AI usage recording and summary.
- Operations daily report.

Validation command:

```bash
make test
make lint
make typecheck
cd frontend && npm run build
```

Release 2 validation passed with 63 backend tests.
