# KiranaOS Roadmap

KiranaOS has reached the intended **prototype-complete** state for the current project. The repository now demonstrates the end-to-end merchant operating model from conversational order capture through review, store operations, payment, settlement, accounting handoff, and audit evidence.

**There are no open MVP feature commitments in this roadmap.** Further work is intentionally demand-driven rather than roadmap-driven. New implementation should begin only when there is a concrete pilot, adoption, integration, production, or reproducible merchant requirement.

This is a feature-complete boundary for the current prototype objective, not a claim that KiranaOS is production-ready or permanently frozen.

## Completed: Release 1 Commercial Foundation, v2.3.0

Release 1 stabilized the repository for controlled pilots: provider correctness, ingestion safety, review/correction workflow, auth-enabled pilot UI, auditability, tests, and adoption documentation.

## Completed: Release 2 Operations Release, v2.4.0

Release 2 made KiranaOS useful as a daily merchant operations demonstrator: product catalog management, substitutions, product binding, repeat orders, customer history, staff assignment, order notes, daily operations reporting, feature flags, and AI usage tracking.

## Completed: Release 3 Order-to-Cash Release, v2.5.0

Release 3 established the monetizable workflow surface: cash, UPI, and split payments; order reconciliation; controlled refunds and cancellations; daily settlement closure; and accountant-ready CSV/XLSX exports.

## Completed: Prototype closeout, August 2026

The closeout checkpoint makes the repository meaningful as a durable reference implementation rather than an unfinished feature sequence.

Acceptance criteria:

- The intended outcome is explained through an end-to-end demo walkthrough.
- Implemented capabilities and deferred production requirements are explicitly separated.
- Backend tests, linting, and type checking are represented in CI.
- Frontend linting and build are represented in CI.
- Documentation integrity is represented in CI and GitHub Pages publication remains supported.
- `make verify` provides one local acceptance gate.
- Repository hygiene excludes generated, environment, and workstation artifacts.
- No future platform or production feature is implied to be required for the prototype to be considered complete.

## Future development: issue-led intake

Future product work starts with the **Feature or adoption request** issue template in `.github/ISSUE_TEMPLATE/feature-request.md`. Engineering defects and reproducible implementation gaps continue to use the existing **Engineering gap** template.

Opening a feature request does not create a roadmap commitment. A request should be promoted into a future roadmap tranche only when all of the following are true:

1. **Demand is evidenced.** There is a concrete merchant, adopter, pilot, integration, or production signal rather than a speculative feature idea.
2. **The outcome fits KiranaOS.** The capability advances the merchant operating model and has a clear repository ownership boundary.
3. **Authority and risk are understood.** Write authority, payment/accounting effects, customer data, AI behavior, external integrations, security, privacy, and compatibility implications are explicit where relevant.
4. **A smallest useful slice exists.** The request can be implemented as a bounded proposition rather than an open-ended platform expansion.
5. **Success is testable.** Acceptance evidence, including important negative cases, can be stated before implementation.
6. **Value justifies complexity.** Adoption value is proportionate to implementation, operational, dependency, and maintenance cost.

Once promoted, substantive work should follow the repository's Issue → implementation → tests → PR → CI → merge/release discipline. The roadmap should be updated only when a promoted request creates a real delivery commitment.

## Deferred candidate pool — not commitments

The former “Release 4 Partner and Platform Foundations” is no longer an active release commitment. The following capabilities are retained only as context for future demand; their presence here must not be interpreted as planned work:

- plan/quota enforcement and billing;
- API keys and external partner webhooks;
- partner-sponsored onboarding;
- multi-store portfolio/partner console;
- distributor-sponsored flows;
- offline-first synchronization;
- vertical-specific packs;
- production infrastructure hardening, SLOs, observability, backup/recovery, and scale testing;
- formal payment/compliance integrations.

These items are productization work, not missing proof-of-concept functionality. They should be reconsidered only when issue evidence establishes a concrete need.

## Explicitly not planned without a new project mandate

- autonomous agents with direct write authority;
- credit scoring;
- advanced dynamic pricing;
- marketplace orchestration;
- distributor monetization before a validated merchant adoption case exists.

See `docs/PROJECT_STATUS.md` for the formal prototype boundary and `docs/DEMO_WALKTHROUGH.md` for the shortest path through the intended outcome.
