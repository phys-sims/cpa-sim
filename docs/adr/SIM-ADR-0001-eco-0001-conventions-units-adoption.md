# SIM-ADR-0001: Adopt ECO-0001 conventions and units policy in cpa-sim

- **Status:** Proposed
- **Date:** 2026-02-16
- **Mapped ecosystem ADR:** [ECO-0001](../../../../docs/adr/ECO-0001-conventions-units.md)

## Decision
Adopt ECO-0001 in `cpa-sim` as the governing policy for naming, units, and coordinate/frame conventions.

## Inherited from ecosystem ADR (verbatim vs summarized)
Source of truth is ECO-0001; this ADR records local adoption intent.

Inherited policy summary:
- Use one canonical unit system with explicit unit metadata at interfaces.
- Enforce unambiguous naming for quantities and coordinate/frame identifiers.
- Require docs/tests to validate unit expectations and conversions where applicable.
- Treat ecosystem conventions as normative for inter-repo compatibility.

## Repo-local extension/override
No repo-local extension at this time.

## Implications for this repo
- Existing and new `cpa-sim` interfaces should continue exposing units explicitly in schemas and docs.
- ADR-driven unit and naming checks should be reflected in local tests as they are expanded.
- Internal docs should reference ECO-0001 rather than redefining conventions locally.

## Migration notes
- `STATUS.md` should track any remaining unit-normalization TODOs against this adoption record.
- `docs/roadmaps/v1_to_v3_plan.md` placeholders should reference ECO-0001 through this ADR when work items are concretized.

## References
- Ecosystem source of truth: [ECO-0001 Conventions and units](../../../../docs/adr/ECO-0001-conventions-units.md)
- Local status tracker: [`STATUS.md`](../../STATUS.md)
- Local roadmap: [`docs/roadmaps/v1_to_v3_plan.md`](../roadmaps/v1_to_v3_plan.md)
