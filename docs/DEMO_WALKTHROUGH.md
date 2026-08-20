---
layout: default
title: Demo Walkthrough
nav_order: 2
permalink: /demo/
---

# KiranaOS Demo Walkthrough

This walkthrough is the shortest path to understanding what KiranaOS is intended to accomplish. It uses the local simulation path so that the core workflow can be evaluated without WhatsApp, OCR, speech-to-text, payment-provider, or cloud credentials.

## What the demo should prove

A customer can remain in a familiar conversational ordering channel while the merchant receives a structured operational object that can be reviewed, corrected, fulfilled, paid, reconciled, and audited.

The important architectural boundary is that **message interpretation does not itself grant operational authority**. Parsing proposes structure. Merchant workflows decide what becomes actionable.

## 1. Start the stack

```bash
git clone https://github.com/sankarshanmukhopadhyay/kiranaos.git
cd kiranaos
make dev
```

Open `http://localhost:5173`. The API documentation is available at `http://localhost:8000/docs`.

For local evaluation, external AI providers are optional. Text inputs and the simulation path are sufficient to understand the workflow.

## 2. Create or inspect an inbound order

Use **Simulate WA order** in the application sidebar. The simulated message exercises the same normalized ingestion boundary used by provider adapters.

Observe the resulting order and its source evidence. The order is no longer only an unstructured chat message: customer, items, quantities, source, confidence/review state, and lifecycle status can now be handled explicitly.

**Evidence to inspect:** the order record, inbound-message evidence, source/input method, parsed items, and any review state.

## 3. Exercise the human-review boundary

Choose an order requiring review, or alter item data through the review/correction workflow.

The expected behavior is that uncertain interpretation does not silently become a fulfillment instruction. An operator can correct items and explicitly resolve the review before the order returns to the normal pending workflow.

**Authority:** operator action.

**Evidence:** corrected items, review-resolution state, and audit event.

## 4. Move the order through store operations

Move a valid order through the guarded lifecycle such as pending → packing/packed → delivered. Where useful, bind items to catalog products, add operational notes, assign staff, or attach a delivery assignment.

The prototype also exposes repeat-order and customer-history flows to demonstrate that KiranaOS is intended to become a merchant operations memory rather than a one-message parser.

**Authority:** role-scoped merchant operator/manager actions.

**Evidence:** order status, assignments, notes, catalog bindings, delivery state, and audit history.

## 5. Inspect the customer and udhaari context

Open the customer record and ledger. KiranaOS keeps credit/udhaari visible beside the operational history and can surface dormant customers.

This demonstrates a core product hypothesis: the useful merchant system is not merely an order inbox. It is a small operational state machine around the commercial relationship.

**Evidence:** customer history, ledger entries, current credit balance, recent orders, dormant status where applicable.

## 6. Complete order-to-cash

Set an order amount if needed, then record a payment using the available payment flows. The prototype supports cash, UPI, and split tender. Inspect the order payment summary to confirm paid, refunded, net-paid, and outstanding values.

If demonstrating an exception, use the governed refund or cancellation path rather than rewriting financial state directly.

**Authority:** normal payment capture is operational; refund approval and settlement closure are more tightly role-scoped.

**Evidence:** payment records, reconciliation summary, refund/cancellation records, and financial audit events.

## 7. Generate the daily settlement

Create the daily settlement and inspect the separation of cash, UPI, refunds, and net receipts. Where authentication/roles are enabled, close the settlement using an owner-authorized account.

Export accounting evidence as CSV or XLSX to demonstrate the handoff boundary to an accountant or downstream POS/accounting process.

**Evidence:** settlement record, closure event, export artifact, and audit event.

## 8. Inspect the audit trail

Use the audit endpoint or relevant UI surfaces to inspect sensitive mutations made during the demonstration. The audit trail is the connective tissue between the product workflow and the governance model: a material state change should have an attributable action, scope, and evidence record.

## 9. Verify the repository

Run the prototype acceptance gate:

```bash
make verify
```

The same quality gates run in GitHub Actions. A successful result proves that the repository is internally coherent at the prototype level: backend behavior is tested and typed, frontend code builds, and the documentation graph is publishable.

## What this walkthrough does not prove

A successful demonstration does **not** establish production readiness, security certification, payment compliance, high-scale reliability, or operational suitability for unsupervised deployment. Those requirements are explicitly deferred in the [Prototype Status]({% link PROJECT_STATUS.md %}) document.

## Mental model

The intended outcome can be summarized as:

```text
Customer message
      │
      ▼
Normalized ingestion
      │
      ▼
Interpretation / confidence
      │
      ├── uncertain ──► human review ──┐
      │                                │
      └──────────── valid ─────────────┘
                       │
                       ▼
                 Structured order
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
      customer      fulfilment    delivery
      context          work          work
         └─────────────┼─────────────┘
                       ▼
                payment / credit
                       │
                       ▼
                   settlement
                       │
                       ▼
             accounting + audit
```

That is the KiranaOS prototype: conversational demand on one side, governed merchant operations on the other.
