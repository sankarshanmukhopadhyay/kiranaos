feat: harden KiranaOS provider ingestion and repo readiness

Use the KiranaOS v2 FastAPI/React codebase as the base and merge in the stronger production
ingestion ideas from the prior rebuilt repo.

- Add provider metadata to inbound messages: source, external message id, media type, extracted text, and parse status
- Add concrete Twilio WhatsApp webhook at `/api/webhooks/twilio/whatsapp`
- Add Twilio signature validation using `KIRANA_TWILIO_AUTH_TOKEN`
- Add optional OpenAI item extraction adapter while keeping the core parser pure
- Preserve normalized order items, item confidence, udhaari ledger, customer dormancy, and analytics endpoints
- Fix customer detail route import hygiene
- Add Twilio webhook integration test
- Move embedded frontend CSS into `frontend/src/styles.css`
- Move sidebar labels/icons into `frontend/src/sidebarMeta.tsx`
- Fix CI frontend install path by avoiding a missing lockfile assumption
- Refresh README, architecture, and environment documentation
