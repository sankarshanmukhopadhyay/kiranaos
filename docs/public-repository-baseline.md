# Public repository baseline

This record captures controls reviewed under issue #8. It is repository assurance evidence, not external certification.

| Control | State | Evidence | Residual risk |
|---|---|---|---|
| Purpose/maturity/adoption | PASS | `README.md`, `PROJECT-STATUS.yaml`, `ROADMAP.md`, demos/docs | None identified. |
| Licensing/release provenance | PASS | `LICENSE`, `CHANGELOG.md` | Publication remains maintainer judgment. |
| Security reporting | PASS | `SECURITY.md` | Hosted private-reporting enablement remains platform evidence. |
| Contribution/community/support | PASS | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, issue/PR templates | None identified. |
| Dependency updates | PASS | `.github/dependabot.yml` | Hosted Dependabot enablement remains platform evidence. |
| Default-branch protection | EVIDENCE REQUIRED | rulesets API returned no active ruleset on 2026-09-05 | Tracked separately as a repository-setting control. |
| CI/tests/deployment | PASS / bounded | workflows, Makefile, backend/frontend/tests, compose/demo surfaces | Workflow green does not prove production deployment safety. |
| Authority boundary | PASS | README/docs/security | KiranaOS owns its implementation; external protocols/infrastructure retain their authority. |

## Completion boundary

Repository-owned baseline gaps are closed by the remediation PR. Default-branch protection remains a GitHub-hosted residual tracked separately rather than represented as PASS.
