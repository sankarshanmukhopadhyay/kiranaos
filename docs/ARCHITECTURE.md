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
│          ├─ OCR adapter (optional)    │  ← Google Vision for photos
│          ├─ parser.py                 │  ← text → [ParsedItem]
│          └─ creates Order + Items     │  ← normalised, queryable
│                                       │
│  REST API                             │
│    /orders     /customers             │
│    /analytics  /dashboard/summary     │
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
| `find_or_create_customer` upsert | Phone is the identity key; no duplicate customers across messages |
| SQLite default → Postgres in prod | Zero setup for development; `KIRANA_DATABASE_URL` swap for production |

## Ingestion pipeline

```
IngestMessageIn (normalised payload)
    │
    ├── message_type = text   →  parse_order_text(text)
    ├── message_type = image  →  OCR adapter → parse_order_text(ocr_text)
    └── message_type = voice  →  [STT adapter, not yet configured]
                                   → parse_order_text(transcript)

parse_order_text returns [ParsedItem(name, quantity, unit, confidence)]

If parsed_items is empty   →  Order.status = needs_review
If parsed_items present    →  Order.status = pending
```

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
- Add Alembic for schema migrations before going multi-store
- Attach Google Vision to the OCR adapter: set `KIRANA_GOOGLE_VISION_KEY_JSON`
- Configure `KIRANA_TWILIO_AUTH_TOKEN` and `KIRANA_PUBLIC_BASE_URL` before exposing Twilio webhooks
- Configure `KIRANA_OPENAI_API_KEY` only if the heuristic parser needs long-tail language support
- Add operator authentication (JWT or session) before public deployment
- Consider per-store multi-tenancy: add `store_id` FK to Customer and Order
- Keep raw media retention short; document customer consent expectations
