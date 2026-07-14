---
layout: page
title: AI Providers
permalink: /ai-providers/
---

# AI Providers

KiranaOS's order-ingestion pipeline has three optional AI-assisted
steps. Each is a pluggable adapter behind a provider dispatcher; none
is required, and each defaults to its original (pre-Sarvam) provider
so existing deployments see no behaviour change until you opt in.

| Capability | Contract | Default provider | Sarvam alternative | Dispatcher |
|---|---|---|---|---|
| Speech-to-text | `transcribe(media_url, media_type) -> str \| None` | OpenAI Whisper (`whisper-1`) | Sarvam Saaras (`saaras:v2`) | `app/services/voice.py` |
| Photo/handwriting OCR | `extract_text(media_url) -> str` | Google Cloud Vision | Sarvam Vision (document digitization) | `app/services/ingestion.py` provider branch |
| Parser fallback (unparsed text) | `extract_items(text) -> list[str] \| None` | OpenAI (`gpt-4o-mini`) | Sarvam Chat (`sarvam-m`, OpenAI-compatible `/v1/chat/completions`) | `app/services/adapters.py` |

None of these steps can place an order on their own. Every path — rule-based
parser, OpenAI, or Sarvam — feeds back into the same `parse_order_text()` /
`needs_review` gate in `ingestion.py`. An AI provider can improve the odds
an order is auto-accepted; it cannot bypass the confidence check that
decides that.

## Why Sarvam fits this problem specifically

KiranaOS's actual input is Hindi/Telugu/Marathi/Tamil grocery orders,
frequently code-mixed with English mid-sentence ("Rajasthan ke liye
5kg atta, dal 1kg"). This is Sarvam's stated training focus — Saaras
and Sarvam-30B/105B are trained on code-mixed Indic input natively,
rather than as an English-first model with Indic support layered on.
Whether this yields a measurable accuracy improvement over the existing
OpenAI/Google Vision path for *this* store's message patterns is an
empirical question — see the recommended rollout below — not something
to assume from vendor positioning alone.

## Enabling Sarvam

Each capability is switched independently:

```bash
# .env or KIRANA_* environment variables
KIRANA_SARVAM_API_KEY=your-sarvam-key

KIRANA_STT_PROVIDER=sarvam          # default: openai
KIRANA_OCR_PROVIDER=sarvam          # default: google_vision
KIRANA_PARSER_AI_PROVIDER=sarvam    # default: openai

KIRANA_SARVAM_STT_MODEL=saaras:v2        # default in .env.example
KIRANA_SARVAM_LLM_MODEL=sarvam-m         # default in .env.example; swap only after testing
```

Unknown provider values fail configuration validation at startup. Set a provider to `none` for review-only mode.

## Recommended rollout (not yet executed — this is guidance, not a claim of production use)

1. Enable one capability at a time, starting with `KIRANA_PARSER_AI_PROVIDER=sarvam`
   — lowest blast radius, since it only fires when the rule-based parser
   already found zero items.
2. Compare `needs_review` volume before/after over a representative
   week per store; Sarvam should reduce it if the accuracy claim holds
   for your customers' actual message patterns.
3. Only then enable STT/OCR, since those touch raw audio/image content
   leaving your infrastructure — see data-residency note below.

## Trust, evidence, and authority (see also `docs/SECURITY_MODEL.md`)

- **Authority**: AI providers write to `InboundMessage.extracted_text`
  only. They never write `Order`, `Customer`, or `LedgerEntry` rows
  directly — the rule-based parser and existing order-creation code
  path remain the sole authority for what becomes an order.
- **Evidence**: which provider produced a given message's text is
  visible via `KIRANA_*_PROVIDER` at time of ingestion; if you need
  per-message provider attribution for audit purposes, extend
  `AuditEvent.evidence` (not yet implemented — flagged, not claimed).
- **Revocation**: disable a provider by unsetting `KIRANA_SARVAM_API_KEY`
  or setting the relevant `*_PROVIDER=none`; no data migration is
  required since these adapters are stateless per-request calls.
- **Data residency**: enabling Sarvam sends customer order audio/photos/
  text to Sarvam's API (India-hosted, per Sarvam's published
  infrastructure) instead of / in addition to OpenAI/Google (US-hosted).
  If your store operates under a data-residency requirement, this is a
  material difference worth reviewing before enabling STT/OCR, not just
  a vendor swap.

## Rate limits (verify before production traffic — pinned to docs.sarvam.ai)

Sarvam's document-digitization (Vision/OCR) endpoint is rate-limited
uniformly across plan tiers at the time of writing; check
`docs.sarvam.ai/api-reference-docs/getting-started/ratelimits` for the
current limit before assuming linear scaling with a plan upgrade, and
queue photo-order ingestion if your peak volume could exceed it.

## Testing

```bash
cd backend
pip install -e ".[dev]"          # installs respx, used to mock Sarvam's HTTP layer
pytest tests/test_sarvam_adapters.py -v
```

This test module never calls the real Sarvam API and never requires a
real API key — it validates the adapters' request/response contracts
against Sarvam's documented schemas using mocked HTTP responses. See
the conformance matrix below.

## Conformance matrix

| Adapter | Passing case | Failing case |
|---|---|---|
| STT (Saaras) | Well-formed audio + 200 response → returns transcript string | Upstream 5xx → returns `None`, does not raise |
| Vision OCR | Well-formed image + 200 response → returns extracted text | Upstream 5xx → returns `""`, does not raise |
| LLM parser fallback | Well-formed prompt + valid JSON content → returns item list | Malformed JSON in response content → returns `None`, does not raise |
| Provider dispatch | Unset `KIRANA_*_PROVIDER` → defaults to pre-Sarvam provider | Unknown provider string → returns `None`/`""`, logs a warning, never raises |

Every row above has a corresponding passing and failing test in `backend/tests/test_sarvam_adapters.py`. Release 1 validation passed with 57 backend tests.

## What is not yet done (explicitly out of scope for this change)

- No real Sarvam API key has been used against the live API — all
  validation here is contract-level (mocked HTTP), not a live-traffic
  accuracy comparison.
- No per-provider audit trail (`AuditEvent.evidence.model_name`) is
  wired in yet — flagged in the section above.
- Sarvam is not applicable to route optimization or credit-risk
  scoring (numeric/tabular problems outside Sarvam's language-model
  focus); those remain out of scope for this integration.
