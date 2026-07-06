# Security Model

## Trust Boundaries

| Boundary | Control |
|---|---|
| Operator API | JWT bearer token and store-scoped role checks |
| WhatsApp inbound | Provider verification and normalized ingestion |
| WhatsApp outbound | Provider-specific credentials and recorded dispatch evidence |
| UPI webhook | HMAC signature and timestamp replay tolerance |
| Media fetch | SSRF checks before OCR or transcription fetches |
| Store tenancy | `store_id` on operational records and scoped queries |

## Delegation And Scope

Operators act within a store. Roles delegate authority by workflow, not just by page access. The release intentionally distinguishes owner governance, manager control-plane actions, and staff execution actions.

## Revocation

Operator revocation should be performed by disabling or removing the operator account and rotating JWT secrets if active tokens must be invalidated immediately. Provider secrets should be rotated through the provider dashboard and deployment environment.

## Auditability

Sensitive mutations produce `AuditEvent` records with action, entity, actor, timestamp, and evidence JSON. These events are designed to support operational review and lightweight assurance.
