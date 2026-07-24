---
layout: default
title: Release 2 Operations Guide
parent: Operations
nav_order: 2
permalink: /operations/release-2/
---

# Release 2 Operations Guide

Release 2 turns KiranaOS into a daily operations workflow for controlled pilots. The release is intended for merchants who need structured order capture, catalog-backed fulfillment, repeat orders, staff allocation, and daily reporting.

## Operating model

The workflow is deliberately conservative:

1. Customer messages create orders or review items.
2. Operators correct ambiguous items.
3. Corrected items may be bound to catalog products.
4. Substitutions are recorded explicitly.
5. Orders can be assigned to staff for fulfillment.
6. Daily reports produce operational evidence.
7. AI usage is tracked as a cost signal, not as an authority decision.

## Catalog workflow

Use the catalog to maintain products that can be packed, priced, substituted, and reported.

Recommended fields:

- `sku`: store-scoped stable identifier.
- `name`: operator-facing product name.
- `canonical_name`: normalized name used across variants and reports.
- `category`: shelf or business category.
- `unit`: default selling/packing unit.
- `price`: optional pilot price.
- `stock_quantity`: optional operational stock hint.
- `status`: `active` or `inactive`.

## Substitution workflow

Substitutions are not automatic fulfillment decisions. They are approved operational alternatives. A substitution record means the store has decided that product B can substitute product A under stated conditions.

## Repeat order workflow

Use repeat orders for customers who ask for the same basket again. The generated order copies items and amount metadata from the source order but records a new order and audit event.

## Staff assignment workflow

Staff assignments allocate work without changing order ownership. The supported lifecycle is:

- `assigned`
- `accepted`
- `completed`
- `reassigned`
- `cancelled`

Managers create assignments. Staff can update assignment status.

## AI usage workflow

AI usage events should be recorded when external AI providers are used for parsing, OCR, STT, or review assistance. The system records provider, model, purpose, estimated units, estimated cost, success, and failure reason.

This does not enforce quotas or billing. It creates evidence for Release 3 and later pricing work.
