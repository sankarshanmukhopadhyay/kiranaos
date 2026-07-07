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
│   │   │   ├── auth.py            # Operator auth, JWT issuance, store scope
│   │   │   ├── operations.py      # Delivery, outbound confirmation, UPI reconciliation
│   │   │   ├── parser.py          # Text → [ParsedItem] (pure function, no I/O)
│   │   │   ├── stt/               # Speech-to-text provider dispatch (see docs/AI_PROVIDERS.md)
│   │   │   │   ├── openai_whisper.py  # Default STT provider
│   │   │   │   └── sarvam.py          # Optional: Sarvam Saaras STT
│   │   │   ├── ocr/               # OCR provider dispatch
│   │   │   │   ├── google_vision.py   # Default OCR provider
│   │   │   │   └── sarvam_vision.py   # Optional: Sarvam Vision OCR
│   │   │   └── llm/               # Parser-fallback LLM provider dispatch
│   │   │       ├── openai_chat.py     # Default fallback provider
│   │   │       └── sarvam_chat.py     # Optional: Sarvam Chat (sarvam-30b)
│   │   └── main.py                # FastAPI app factory
│   ├── tests/
│   │   ├── test_parser.py         # Parser unit tests (14 cases, pure function)
│   │   ├── test_api.py            # API integration tests (in-memory SQLite)
│   │   └── test_sarvam_adapters.py # Sarvam adapter conformance tests (mocked HTTP)
│   ├── Dockerfile
│   ├── alembic/                   # Production migration baseline
│   ├── alembic.ini
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
├── docs/                         # Architecture, adoption, API, deployment, security, release notes
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

### Stores & Operators
| Method | Path | Description |
|---|---|---|
| `POST` | `/stores` | Create a store / franchise tenant |
| `GET` | `/stores/current` | Resolve the active store scope |
| `POST` | `/operators` | Create an operator account |
| `POST` | `/auth/login` | Issue an HS256 JWT for an operator |

### Orders
| Method | Path | Description |
|---|---|---|
| `GET` | `/orders` | List orders. Filter: `?status=pending&customer_id=1` |
| `GET` | `/orders/{id}` | Single order with customer + items |
| `PATCH` | `/orders/{id}/status` | Advance: pending → packed → delivered |
| `PATCH` | `/orders/{id}/amount` | Set amount and udhaari flag |
| `POST` | `/orders/{id}/confirmations` | Record/send outbound WhatsApp order confirmation |

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

### Delivery
| Method | Path | Description |
|---|---|---|
| `POST` | `/delivery/agents` | Create a delivery agent |
| `GET` | `/delivery/agents` | List active delivery agents |
| `POST` | `/orders/{id}/delivery` | Assign an order to an agent with route order |
| `PATCH` | `/delivery/assignments/{id}/status` | Update assignment lifecycle |
| `GET` | `/delivery/agents/{id}/route` | Route-ordered delivery stop list |
| `POST` | `/delivery/routes/optimize` | Optimize route ordering for assigned stops |

### Payments
| Method | Path | Description |
|---|---|---|
| `POST` | `/payments/upi/webhook` | Reconcile UPI payment events to customer credit/order state |

### Audit
| Method | Path | Description |
|---|---|---|
| `GET` | `/audit/events` | Store-scoped audit events for sensitive operational mutations |

---

## Configuration

All settings use the `KIRANA_` prefix. Copy `backend/.env.example` to `backend/.env`.

| Variable | Default | Description |
|---|---|---|
| `KIRANA_DATABASE_URL` | `sqlite:///./data/kiranaos.db` | SQLite for dev; set to `postgresql://...` for production |
| `KIRANA_DEFAULT_STORE_ID` | `1` | Store scope used in demo mode and unauthenticated local development |
| `KIRANA_WHATSAPP_VERIFY_TOKEN` | `change-me` | Secret token for Meta webhook verification |
| `KIRANA_PUBLIC_BASE_URL` | `http://localhost:8000` | Public API origin used for Twilio signature validation |
| `KIRANA_TWILIO_AUTH_TOKEN` | — | Twilio auth token; when set, webhook signatures are enforced |
| `KIRANA_TWILIO_ACCOUNT_SID` | — | Twilio account SID for outbound WhatsApp |
| `KIRANA_TWILIO_WHATSAPP_FROM` | — | Twilio WhatsApp sender number |
| `KIRANA_WHATSAPP_PROVIDER` | `simulation` | Outbound provider: `simulation`, `twilio`, or `meta` |
| `KIRANA_META_WHATSAPP_TOKEN` | — | Meta Cloud API token for outbound WhatsApp |
| `KIRANA_META_PHONE_NUMBER_ID` | — | Meta phone number id for outbound WhatsApp |
| `KIRANA_PROVIDER_TIMEOUT_SECONDS` | `20` | Outbound provider HTTP timeout |
| `KIRANA_FRONTEND_ORIGIN` | `*` | CORS origin; set to your frontend domain in production |
| `KIRANA_AUTH_REQUIRED` | `false` | Require bearer JWTs for store-scoped API routes |
| `KIRANA_JWT_SECRET` | `change-me` | HS256 JWT signing secret |
| `KIRANA_JWT_EXPIRY_MINUTES` | `480` | Operator session lifetime |
| `KIRANA_UPI_WEBHOOK_SECRET` | — | Shared secret for signed UPI webhook callbacks |
| `KIRANA_GOOGLE_VISION_KEY_JSON` | — | GCP service account JSON (for OCR) |
| `KIRANA_OPENAI_API_KEY` | — | Optional parser enhancement and voice note transcription |
| `KIRANA_OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Audio transcription model used for voice notes |
| `KIRANA_SARVAM_API_KEY` | — | Sarvam AI key; enables the Sarvam STT/OCR/parser-fallback adapters |
| `KIRANA_STT_PROVIDER` | `openai` | `openai` \| `sarvam` \| `none` |
| `KIRANA_OCR_PROVIDER` | `google_vision` | `google_vision` \| `sarvam` \| `none` |
| `KIRANA_PARSER_AI_PROVIDER` | `openai` | `openai` \| `sarvam` \| `none` |
| `KIRANA_SARVAM_STT_MODEL` | `saaras:v3` | Sarvam STT model |
| `KIRANA_SARVAM_LLM_MODEL` | `sarvam-30b` | Sarvam chat model for parser fallback; `sarvam-105b` for higher quality |
| `KIRANA_LOG_LEVEL` | `INFO` | Python logging level |

---

## Third-party setup

### WhatsApp (Twilio or Meta Cloud API)

Twilio has a concrete inbound endpoint at `/api/webhooks/twilio/whatsapp`. It validates
`X-Twilio-Signature` when `KIRANA_TWILIO_AUTH_TOKEN` is configured, maps Twilio's form payload to
`IngestMessageIn`, and returns empty TwiML immediately after ingestion.

The generic `/api/webhooks/whatsapp` POST route is retained as a provider-neutral entry point for
future Meta Cloud API payload mapping. The `IngestMessageIn` schema is the normalised shape that
`ingest_message()` expects.

Outbound order confirmations use `KIRANA_WHATSAPP_PROVIDER`. `simulation` records a local evidence
event without sending a provider message. `twilio` and `meta` dispatch through their provider APIs
and preserve provider message ids, dispatch attempts, status, and failure reasons.

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
Run the included Alembic migration baseline before going live:

```bash
make migrate
```

---


### v2.2.0 maturity release

The v2.2.0 maturity release completes the adoption roadmap:

- provider-aware outbound WhatsApp confirmations for simulation, Twilio, and Meta;
- deterministic delivery route optimization with geocoded nearest-neighbour routing and address-sort fallback;
- consistent role-based authority across owner, manager, and staff workflows;
- audit events for order, credit, outbound, delivery, route, and payment mutations;
- production environment template, CI workflows, release archive workflow, changelog, and expanded documentation.

See [`docs/RELEASE_NOTES_v2.2.0.md`](docs/RELEASE_NOTES_v2.2.0.md) for full release notes.

### Security hardening

The v2.1.1 hardening release closes the main red-team findings from the operational roadmap release:

- store and operator creation are role-gated when `KIRANA_AUTH_REQUIRED=true`;
- JWT decoding now validates header claims, expiry, required claims, and signatures defensively;
- production-style startup fails closed when demo secrets are still configured;
- Twilio webhook signature bypass is limited to demo mode;
- UPI webhook callbacks can be HMAC-signed with timestamp replay protection;
- media URLs are validated before OCR/transcription fetches to reduce SSRF exposure;
- CORS no longer defaults to wildcard credentials;
- UPI duplicate detection is scoped by store to avoid cross-tenant leakage.

See [`SECURITY.md`](SECURITY.md) for the production checklist and trust-boundary details.

## Roadmap

- [x] Voice note transcription through a configurable OpenAI or Sarvam Saaras audio adapter, with safe `needs_review` fallback when no key is configured — see `docs/AI_PROVIDERS.md`
- [x] Outbound WhatsApp confirmation records for order lifecycle events, simulated locally and ready for provider dispatch
- [x] Delivery assignment, delivery status lifecycle, and route-ordered agent stop lists
- [x] UPI payment webhook reconciliation against customer credit and order state
- [x] Alembic migration baseline for production schema management
- [x] Multi-store / franchise support with `store_id` on operational models and store-scoped service queries
- [x] Operator authentication with HS256 JWTs and optional production enforcement
- [x] Provider-specific outbound WhatsApp dispatch for Twilio and Meta Cloud API
- [x] Route optimization using geocoded customer coordinates with deterministic fallback
- [x] Role-based permissions beyond store-level JWT scope

### Documentation

- [`docs/ADOPTION_GUIDE.md`](docs/ADOPTION_GUIDE.md)
- [`docs/API_GUIDE.md`](docs/API_GUIDE.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md)
- [`docs/TESTING.md`](docs/TESTING.md)

---

## Contributing

1. Fork, create a branch: `git checkout -b feature/voice-transcription`
2. `make test && make lint` must pass before opening a PR
3. Pull requests against `main`

---

## License

MIT © 2026 KiranaOS Contributors
