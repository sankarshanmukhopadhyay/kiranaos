---
layout: page
title: Deployment Guide
permalink: /deployment/
---

# Deployment Guide

## Recommended Stack

| Component | Recommendation |
|---|---|
| API | Railway, Render, Fly.io, or container platform |
| Frontend | Vercel or static hosting |
| Database | Postgres |
| Inbound WhatsApp | Twilio sandbox first, Meta Cloud API for production |
| Outbound WhatsApp | `twilio` or `meta` provider mode |

## Production Steps

1. Copy `.env.production.example`.
2. Replace all placeholder secrets.
3. Set `KIRANA_DATABASE_URL` to Postgres.
4. Run migrations:

```bash
make migrate
```

5. Create the first owner operator.
6. Configure provider webhooks.
7. Run smoke tests against `/api/health`, `/api/dashboard/summary`, and `/docs`.

## Release Guardrails

The API fails closed when production-style settings are enabled with known placeholder secrets. A production deployment should never use wildcard CORS, demo JWT secrets, or unsigned payment webhooks.
