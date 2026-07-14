---
layout: page
title: Architecture
permalink: /architecture/
---

# Architecture

KiranaOS keeps the customer's behaviour unchanged. They continue sending WhatsApp messages,
photos of handwritten lists, and voice notes exactly as before. The system converts those
inbound communications into structured operational records for the shop owner.

## Core flow

```
WhatsApp customer
       │  text / photo / voice note
       ▼
  Provider (Twilio or Meta Cloud API)
       │  Twilio: POST /api/webhooks/twilio/whatsapp
       │  Meta: GET /api/webhooks/whatsapp verification
       ▼
┌──────────────────────────────────────┐
│  FastAPI Backend                      │
│                                       │
│  webhook route                        │
│    └─► ingestion.py                  │
│          ├─ find_or_create_customer   │  ← upsert on phone number
│          ├─ OCR adapter (optional)    │  ← Google Vision or Sarvam Vision
│          ├─ voice adapter (optional)  │  ← OpenAI Whisper or Sarvam Saaras
│          ├─ parser.py                 │  ← text → [ParsedItem]
│          └─ creates Order + Items     │  ← normalised, queryable
│                                       │
│  REST API                             │
│    /orders     /customers             │
│    /analytics  /dashboard/summary     │
│    /delivery   /payments              │
└──────────────┬───────────────────────┘
               │  fetch()
       ┌───────▼───────┐
       │  React frontend│  ← Vite, TypeScript, no UI framework
       │  (Vercel/CDN)  │
       └───────────────┘
```

## Data model decisions

| Decision | Rationale |
|---|---|
| `order_items` is a normalised table, not JSON | Enables per-item analytics: top items, total kg of atta, etc. |
| `confidence` per OrderItem | Surfaces uncertain parses in the UI without blocking the order |
| `needs_review` OrderStatus | Honest state for image/voice orders with no text yet; not a flag |
| `LedgerEntry` audit log | Every credit movement is recorded; `credit_balance` is the running sum |
| `InboundMessage` provider metadata | Preserves source, external message id, media type, extracted text, and parse status |
| `Store` scope on operational records | Enables franchise / multi-store isolation without changing customer behavior |
| `Operator` JWTs | Keeps production access scoped to a store while preserving frictionless demo mode |
| `OutboundMessage` records | Confirms customer communication as an auditable operational event |
| `DeliveryAssignment` records | Separates packing from fulfilment and gives delivery agents route-ordered work |
| `Payment` records | Reconciles UPI provider events to credit balances with immutable ledger entries |
| `find_or_create_customer` upsert | Phone is the identity key within a store; no duplicate customers across messages |
| SQLite default → Postgres in prod | Zero setup for development; `KIRANA_DATABASE_URL` swap plus Alembic for production |

## Ingestion pipeline

```
IngestMessageIn (normalised payload)
    │
    ├── message_type = text   →  parse_order_text(text)
    ├── message_type = image  →  OCR adapter → parse_order_text(ocr_text)
    └── message_type = voice  →  STT adapter, if configured
                                   → parse_order_text(transcript)

If parse_order_text finds zero items, an optional LLM parser-fallback
adapter gets a second pass at the same text before falling back to
needs_review. OCR, STT, and the parser fallback are each independently
pluggable — see docs/AI_PROVIDERS.md for the full provider matrix
(default: OpenAI + Google Vision; optional: Sarvam AI end-to-end).

parse_order_text returns [ParsedItem(name, quantity, unit, confidence)]

If parsed_items is empty   →  Order.status = needs_review
If parsed_items present    →  Order.status = pending
```

## Control surfaces

KiranaOS treats each operational step as an auditable record, not an implicit UI state.

| Capability | Authority boundary | Evidence produced |
|---|---|---|
| Store tenancy | `store_id` on customers, messages, orders, ledger, delivery, payments | Store-scoped query results and JWT store claim |
| Operator auth | `/operators` creates accounts; `/auth/login` issues JWT | Signed token with operator id, role, store id, expiry |
| Outbound confirmation | `/orders/{id}/confirmations` records customer notice | `OutboundMessage` with destination, body, provider, status, sent time |
| Delivery fulfilment | `/orders/{id}/delivery` and assignment status updates | `DeliveryAssignment` with agent, route order, lifecycle state |
| UPI reconciliation | `/payments/upi/webhook` applies provider events | `Payment` plus negative `LedgerEntry` against udhaari balance |

## Parser design

The parser is a pure function: `str → [ParsedItem]`. No I/O, no database, no HTTP.
This makes it fast to test and easy to swap for a different approach (LLM-based, etc.).

It handles:
- Comma, semicolon, newline, and dash-delimited lists
- Leading `quantity unit name` pattern ("2 kg atta")
- Hinglish filler words stripped before storing
- Unit aliases normalised (ltr → l, kgs → kg, etc.)
- Deduplication within a single message
- Confidence scoring: 0.85 with explicit quantity, 0.65 without

## Production notes

- Replace SQLite with Postgres by setting `KIRANA_DATABASE_URL=postgresql://...`
- Run `make migrate` before serving production traffic
- Attach Google Vision to the OCR adapter: set `KIRANA_GOOGLE_VISION_KEY_JSON`
- Configure `KIRANA_OPENAI_API_KEY` to transcribe voice notes and improve long-tail parsing
- Or configure `KIRANA_SARVAM_API_KEY` plus `KIRANA_STT_PROVIDER` / `KIRANA_OCR_PROVIDER` / `KIRANA_PARSER_AI_PROVIDER` to use Sarvam's Indic-language models instead — see `docs/AI_PROVIDERS.md`
- Configure `KIRANA_TWILIO_AUTH_TOKEN` and `KIRANA_PUBLIC_BASE_URL` before exposing Twilio webhooks
- Set `KIRANA_AUTH_REQUIRED=true` and create an operator before public deployment
- Keep raw media retention short; document customer consent expectations


## Security control plane

The control plane is designed around explicit authority and scoped evidence rather than implicit trust in transport endpoints. Operator identity is represented by a signed JWT claim set containing `sub`, `store_id`, `role`, and `exp`. When authentication is required, the active store is derived from the token instead of request payloads. Owner and manager role checks protect store creation, operator provisioning, amount mutation, and credit adjustment.

Provider ingress is separated from operator ingress. Twilio WhatsApp callbacks use the provider signature when configured and fall back only in demo mode. UPI callbacks can be verified with an HMAC signature over the timestamp and raw request body. Timestamp tolerance limits replay risk.

External media is treated as untrusted input. Before OCR or transcription adapters fetch a URL, the host must resolve to publicly routable addresses and must not be loopback, private, link-local, multicast, reserved, or unspecified. This prevents the media pipeline from becoming an SSRF path into local infrastructure.

Tenant isolation is enforced at the query layer and the persistence layer. Customer uniqueness is `(store_id, phone)`, operator uniqueness is `(store_id, username)`, and payment duplicate detection is `(store_id, provider_ref)`. This preserves operational independence across stores while allowing the same customer phone or provider reference to appear in different store contexts.
