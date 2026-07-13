# KiranaOS Roadmap

KiranaOS is managed as a merchant workflow platform, not as an open-ended AI demo. Roadmap items are sequenced by commercial evidence: adoption, retention, operational value, and monetization readiness.

## Now: Release 1 Commercial Foundation, v2.3.0

Release 1 stabilizes the current codebase for controlled pilots.

**In scope**

- Repo health, dependency consistency, CI-ready commands, and release hygiene.
- Provider-correct AI dispatch for STT, OCR, and parser fallback.
- Safe ingestion fallback for text, image, and voice messages.
- Duplicate inbound message protection using provider message ids.
- Review/correction workflow for unparsed orders.
- Guarded order lifecycle transitions.
- Auth-enabled frontend API client and operator login flow.
- Audit events for review resolution, item correction, customer updates, duplicate message handling, and order lifecycle changes.
- Pilot documentation, operator guides, and known limitations.

**Explicitly out of scope**

- Billing and subscription management.
- Distributor dashboards.
- Autonomous agents or MCP orchestration.
- Advanced payment automation.
- Credit scoring or lending decisions.
- Production multi-tenant SaaS administration.

## Next: Release 2 Operations Release

Release 2 should convert the pilot foundation into a daily store operating workflow.

- Product/catalog management.
- Customer edit workflows and household history.
- Repeat order shortcuts.
- Delivery notes and staff handoff.
- Daily order reports and exports.
- Deeper frontend forms for item correction and amount updates.
- Feature flags for paid operational modules.
- AI usage/cost reporting sufficient for pricing experiments.

## Later: Release 3 Order-to-Cash Release

Release 3 should create the first strong monetization surface.

- Payment status per order.
- UPI reference capture and mismatch queue.
- Refund/cancellation workflow.
- Daily settlement exports.
- Accounting/POS adapter interface.
- Pilot billing hooks and plan/quota enforcement.

## Not planned for the current roadmap

- Fully autonomous fulfilment actions.
- Model-driven pricing, lending, or eligibility decisions.
- Distributor-sponsored analytics without explicit consent and data-sharing controls.
- Open-ended agent tooling in the critical order/payment write path.
