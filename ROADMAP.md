# KiranaOS Roadmap

KiranaOS follows a commercially sequenced roadmap. Each release must strengthen adoption, daily retention, or monetization evidence without turning AI into an uncontrolled authority layer.

## Completed: Release 1 Commercial Foundation, v2.3.0

Release 1 stabilized the repository for controlled pilots: provider correctness, ingestion safety, review/correction workflow, auth-enabled pilot UI, auditability, tests, and adoption documentation.

## Completed: Release 2 Operations Release, v2.4.0

Release 2 makes KiranaOS useful for daily merchant operations. The release adds product catalog management, substitutions, order item product binding, repeat orders, customer history, staff assignment, order notes, daily operations reporting, feature flags, and AI usage tracking.

### Release 2 acceptance criteria

- A merchant operator can maintain a simple product catalog.
- Ambiguous order items can be corrected and linked to catalog products.
- Approved substitutions can be recorded without rewriting the original customer request.
- Repeat orders can be generated from historical orders.
- Customer history is queryable without manual database inspection.
- Store staff can be assigned to fulfillment tasks.
- AI usage can be recorded and summarized as an operational cost signal.
- The daily report produces operational evidence for pilots.

## Next: Release 3 Order-to-Cash Release

Release 3 should focus on monetizable workflow surfaces: payment status, reconciliation depth, refund/cancellation handling, daily settlement, accounting export, and pilot billing evidence.

### Candidate scope

- Payment status model and reconciliation UI hardening.
- Refund and cancellation workflow.
- Cash/UPI split handling.
- Daily settlement report.
- CSV/XLSX export for accountant/POS handoff.
- Quota and plan enforcement foundations.
- Stronger operator role boundaries around money movement.

## Later

- Distributor-sponsored flows.
- Multi-merchant partner console.
- API keys and webhooks for platform integrations.
- Offline-first workflows.
- Vertical packs for restaurants, pharmacies, bakeries, and cloud kitchens.

## Not planned for core releases

- Autonomous agents with direct write authority.
- Credit scoring.
- Advanced dynamic pricing.
- Marketplace orchestration.
- Distributor monetization before store operations and order-to-cash evidence are stable.
