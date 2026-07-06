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
