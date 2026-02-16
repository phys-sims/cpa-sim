# SIM-ADR-0003: Adopt ECO-0003 validation tiers and CI marker policy in cpa-sim

- **Status:** Proposed
- **Date:** 2026-02-16
- **Mapped ecosystem ADR:** [ECO-0003](../../../../docs/adr/ECO-0003-validation-tiers-ci-policy.md)

## Decision
Adopt ECO-0003 in `cpa-sim` for validation tier definitions, test marker semantics, and CI gating behavior.

## Inherited from ecosystem ADR (verbatim vs summarized)
Source of truth is ECO-0003; this is a local adoption record.

Inherited policy summary:
- Use ecosystem-defined validation tiers to classify test scope and confidence level.
- Apply standardized CI marker policy for selecting fast/default vs extended validation runs.
- Keep marker semantics stable so cross-repo automation can rely on consistent behavior.
- Document and enforce which tiers are required for merge confidence.

## Repo-local extension/override
No repo-local extension at this time.

## Implications for this repo
- `cpa-sim` test markers and CI config should align to ecosystem tier names and intent.
- Local contributor docs should reference ECO-0003 for authoritative marker/tier definitions.
- Future CI expansions should preserve compatibility with ecosystem validation expectations.

## Migration notes
- `STATUS.md` should track conversion of any legacy/placeholder marker usage into ECO-0003 tiers.
- `docs/roadmaps/v1_to_v3_plan.md` should anchor CI hardening milestones to this adoption ADR.

## References
- Ecosystem source of truth: [ECO-0003 Validation tiers and CI policy](../../../../docs/adr/ECO-0003-validation-tiers-ci-policy.md)
- Local status tracker: [`STATUS.md`](../../STATUS.md)
- Local roadmap: [`docs/roadmaps/v1_to_v3_plan.md`](../roadmaps/v1_to_v3_plan.md)
