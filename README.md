# KiranaOS

**WhatsApp-native order management for kirana store owners.**

Customers keep sending WhatsApp messages exactly as they always have — photos of handwritten lists, voice notes, freeform text in any language. KiranaOS converts those messages into a structured order dashboard. Pending, packing, delivered. Udhaari tracked per customer. Customers silent for two weeks flagged before they switch to Blinkit for good.

No app for customers to download. No change in their behaviour.

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/kiranaos.git
cd kiranaos

# Full stack via Docker (recommended — zero configuration)
make dev

# Or without Docker:
make install        # install Python + Node deps
make dev-api        # terminal 1: API on :8000
make dev-frontend   # terminal 2: frontend on :5173
make seed           # optional: load demo data
```

Open **http://localhost:5173**. Click **"Simulate WA Message"** in the sidebar to watch the full ingestion pipeline run.

The interactive API documentation is at **http://localhost:8000/docs**.

---

## Repository structure

```
kiranaos/
│
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # All FastAPI endpoints
│   │   ├── core/config.py         # Settings (pydantic-settings, KIRANA_ prefix)
│   │   ├── db/session.py          # SQLAlchemy engine + session
│   │   ├── db/seed.py             # Demo data loader
│   │   ├── models/domain.py       # SQLAlchemy ORM models
│   │   ├── schemas/domain.py      # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ingestion.py       # Core business logic (orders, customers, ledger)
│   │   │   ├── parser.py          # Text → [ParsedItem] (pure function, no I/O)
│   │   │   └── ocr/
│   │   │       └── google_vision.py  # OCR adapter for handwritten photos
│   │   └── main.py                # FastAPI app factory
│   ├── tests/
│   │   ├── test_parser.py         # Parser unit tests (14 cases, pure function)
│   │   └── test_api.py            # API integration tests (in-memory SQLite)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Full dashboard — 4 views, real API calls
│   │   ├── lib/api.ts             # Typed API client
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   └── vercel.json
│
├── docs/ARCHITECTURE.md           # Data model decisions, pipeline design
├── .github/workflows/
│   ├── ci.yml                     # Test + lint + type-check on every push
│   └── deploy.yml                 # Deploy to Railway + Vercel on main
├── docker-compose.yml
├── Makefile                       # make dev / test / lint / seed
└── railway.json
```

---

## API reference

All endpoints are prefixed `/api`. Auto-generated docs at `/docs` (Swagger) and `/redoc`.

### Dashboard
| Method | Path | Description |
|---|---|---|
| `GET` | `/dashboard/summary` | Single-call load: pending, packed, delivered today, needs_review, dormant, total credit |

### Orders
| Method | Path | Description |
|---|---|---|
| `GET` | `/orders` | List orders. Filter: `?status=pending&customer_id=1` |
| `GET` | `/orders/{id}` | Single order with customer + items |
| `PATCH` | `/orders/{id}/status` | Advance: pending → packed → delivered |
| `PATCH` | `/orders/{id}/amount` | Set amount and udhaari flag |

### Customers
| Method | Path | Description |
|---|---|---|
| `GET` | `/customers` | All customers. Add `?dormant_only=true` for at-risk |
| `POST` | `/customers` | Create customer directly |
| `GET` | `/customers/{id}` | Customer detail |
| `POST` | `/customers/{id}/credit` | Adjust udhaari (positive = extend, negative = payment) |
| `GET` | `/customers/{id}/ledger` | Full credit history |

### Ingestion
| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/messages` | Normalised ingest endpoint used by all provider adapters |
| `GET` | `/webhooks/whatsapp` | Meta Cloud API verification handshake |
| `POST` | `/webhooks/twilio/whatsapp` | Twilio WhatsApp webhook with signature validation |
| `POST` | `/webhooks/whatsapp` | Generic provider webhook placeholder for future Meta payload mapping |

### Analytics
| Method | Path | Description |
|---|---|---|
| `GET` | `/analytics/daily?days=7` | Per-day order count and revenue |
| `GET` | `/analytics/top-items?days=30` | Most ordered items with total quantity |
| `GET` | `/analytics/input-methods` | Breakdown by text / image / voice |

---

## Configuration

All settings use the `KIRANA_` prefix. Copy `backend/.env.example` to `backend/.env`.

| Variable | Default | Description |
|---|---|---|
| `KIRANA_DATABASE_URL` | `sqlite:///./data/kiranaos.db` | SQLite for dev; set to `postgresql://...` for production |
| `KIRANA_WHATSAPP_VERIFY_TOKEN` | `change-me` | Secret token for Meta webhook verification |
| `KIRANA_PUBLIC_BASE_URL` | `http://localhost:8000` | Public API origin used for Twilio signature validation |
| `KIRANA_TWILIO_AUTH_TOKEN` | — | Twilio auth token; when set, webhook signatures are enforced |
| `KIRANA_FRONTEND_ORIGIN` | `*` | CORS origin; set to your frontend domain in production |
| `KIRANA_GOOGLE_VISION_KEY_JSON` | — | GCP service account JSON (for OCR) |
| `KIRANA_OPENAI_API_KEY` | — | Optional parser enhancement for long-tail multilingual orders |
| `KIRANA_LOG_LEVEL` | `INFO` | Python logging level |

---

## Third-party setup

### WhatsApp (Twilio or Meta Cloud API)

Twilio has a concrete endpoint at `/api/webhooks/twilio/whatsapp`. It validates
`X-Twilio-Signature` when `KIRANA_TWILIO_AUTH_TOKEN` is configured, maps Twilio's form payload to
`IngestMessageIn`, and returns empty TwiML immediately after ingestion.

The generic `/api/webhooks/whatsapp` POST route is retained as a provider-neutral entry point for
future Meta Cloud API payload mapping. The `IngestMessageIn` schema is the normalised shape that
`ingest_message()` expects.

**Twilio sandbox** (fastest to start):
1. Create a Twilio account and enable the WhatsApp Sandbox.
2. Set the inbound webhook URL to `https://your-domain.com/api/webhooks/twilio/whatsapp`.
3. Expose localhost with `ngrok http 8000` during development.

**Meta Cloud API** (production):
1. Create a Meta Developer app with WhatsApp Business.
2. Set the webhook callback URL and paste `KIRANA_WHATSAPP_VERIFY_TOKEN` as the verify token.
3. Meta sends a GET to verify; the route returns the challenge automatically.

### Google Cloud Vision (OCR)

Required only for image orders (handwritten list photos). Text and voice orders work without it.

1. Enable Cloud Vision API in your GCP project.
2. Create a service account with **Cloud Vision API User** role.
3. Download the JSON key.
4. Set `KIRANA_GOOGLE_VISION_KEY_JSON` to the file contents (or use `GOOGLE_APPLICATION_CREDENTIALS`).

The OCR adapter requests `DOCUMENT_TEXT_DETECTION` (better for handwriting than `TEXT_DETECTION`)
with language hints for Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, and English.

---

## Running tests

```bash
make test         # run all tests with coverage
make lint         # ruff linting
make typecheck    # mypy type checking
```

Tests use an in-memory SQLite database. No credentials or external services required.

---

## Deployment

### Railway (API) + Vercel (frontend)

1. Fork the repository.
2. Create a Railway project → connect your fork → set env vars from `.env.example`.
3. Create a Vercel project → connect the `frontend/` directory → set `VITE_API_BASE` to your Railway API URL.
4. Add `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` as GitHub secrets.
5. Push to `main` — CI tests run, then both services deploy automatically.

### Production database (Postgres)

Set `KIRANA_DATABASE_URL=postgresql://user:pass@host:5432/kiranaos`.
Add Alembic for schema migrations before going live:

```bash
cd backend
pip install alembic
alembic init alembic
# configure alembic.ini to use KIRANA_DATABASE_URL
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## Roadmap

- [ ] Voice note transcription (OpenAI Whisper or Google Speech-to-Text)
- [ ] Outbound WhatsApp confirmations ("Order packed, Sunita ji! 🎉")
- [ ] Delivery boy assignment + route optimisation
- [ ] UPI payment webhook reconciliation
- [ ] Alembic migrations for production schema management
- [ ] Multi-store / franchise support (`store_id` on all models)
- [ ] Operator authentication (JWT)

---

## Contributing

1. Fork, create a branch: `git checkout -b feature/voice-transcription`
2. `make test && make lint` must pass before opening a PR
3. Pull requests against `main`

---

## License

MIT © 2026 KiranaOS Contributors
