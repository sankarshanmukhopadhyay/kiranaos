# Security Notes

KiranaOS handles operational store data, customer phone numbers, WhatsApp messages, credit balances, delivery assignments, and payment reconciliation records. This release hardens the control plane around those assets while preserving low-friction local demo mode.

## Trust boundaries

- **Operator API**: `/api/orders`, `/api/customers`, `/api/delivery`, `/api/stores`, and `/api/operators` operate within a store scope. When `KIRANA_AUTH_REQUIRED=true`, JWT bearer authentication determines the active store.
- **Provider webhooks**: Twilio WhatsApp callbacks are accepted only with a valid Twilio signature when `KIRANA_TWILIO_AUTH_TOKEN` is configured. Missing Twilio tokens are accepted only in `KIRANA_DEMO_MODE=true`.
- **Payment webhooks**: UPI callbacks support HMAC verification through `X-Kirana-Signature` and `X-Kirana-Timestamp`. Missing webhook secrets are accepted only in `KIRANA_DEMO_MODE=true`.
- **External media fetches**: image and voice-note media URLs are validated before outbound fetches. Private, loopback, link-local, multicast, reserved, unspecified, malformed, and non-HTTP(S) hosts are rejected to reduce SSRF risk.

## Production checklist

Before exposing the API outside a local environment:

1. Set `KIRANA_DEMO_MODE=false`.
2. Set `KIRANA_AUTH_REQUIRED=true`.
3. Replace `KIRANA_JWT_SECRET` with a long random secret.
4. Replace `KIRANA_WHATSAPP_VERIFY_TOKEN` with a provider-specific secret.
5. Set `KIRANA_FRONTEND_ORIGIN` to the exact frontend origin, not `*`.
6. Configure `KIRANA_TWILIO_AUTH_TOKEN` for Twilio webhook verification.
7. Configure `KIRANA_UPI_WEBHOOK_SECRET` for payment webhook verification.
8. Run Alembic migrations instead of relying on startup table creation.

The application fails closed on startup when production-style flags are enabled with known placeholder secrets.

## Role model

Roles are intentionally small:

- `owner`: can create stores and operators for the current store.
- `manager`: can perform higher-risk operational mutations such as amount updates and credit adjustments.
- `staff`: can use authenticated store-scoped reads and lower-risk workflows.

The first operator may be bootstrapped without an existing bearer token. After an operator exists and auth is enabled, further operator creation requires an owner token.

## Evidence produced

Security-relevant events produce durable records in the operational database:

- inbound messages
- orders and parsed items
- outbound confirmations
- credit ledger entries
- delivery assignments
- payment reconciliation records

This gives the system an auditable chain from inbound message to order, delivery, credit, and payment state.
