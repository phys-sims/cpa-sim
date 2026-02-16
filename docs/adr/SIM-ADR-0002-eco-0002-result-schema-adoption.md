# SIM-ADR-0002: Adopt ECO-0002 result schema contract in cpa-sim

- **Status:** Proposed
- **Date:** 2026-02-16
- **Mapped ecosystem ADR:** [ECO-0002](../../../../docs/adr/ECO-0002-result-schema-contract.md)

## Decision
Adopt ECO-0002 in `cpa-sim` as the baseline contract for emitted result artifacts and harness-facing payload structure.

## Inherited from ecosystem ADR (verbatim vs summarized)
Source of truth is ECO-0002; this ADR captures adoption for `cpa-sim`.

Inherited policy summary:
- Emit result payloads that conform to the ecosystem result schema contract.
- Include required provenance/context fields expected by downstream tooling.
- Maintain compatibility with ecosystem consumers by preserving contract semantics.
- Version and evolve schema usage via ecosystem ADR process, not ad hoc local divergence.

## Repo-local extension/override
No repo-local extension at this time.

## Implications for this repo
- Any `cpa-sim` result serialization and fixture generation must align with ECO-0002-required fields.
- Local docs and examples should point to ECO-0002 for schema definitions.
- Contract-focused tests in `cpa-sim` should be organized to detect schema drift early.

## Migration notes
- `STATUS.md` should capture remaining placeholder/result-format cleanup work under ECO-0002 adoption.
- `docs/roadmaps/v1_to_v3_plan.md` should map schema rollout milestones to this ADR rather than duplicating the contract.

## References
- Ecosystem source of truth: [ECO-0002 Result schema contract](../../../../docs/adr/ECO-0002-result-schema-contract.md)
- Local status tracker: [`STATUS.md`](../../STATUS.md)
- Local roadmap: [`docs/roadmaps/v1_to_v3_plan.md`](../roadmaps/v1_to_v3_plan.md)
