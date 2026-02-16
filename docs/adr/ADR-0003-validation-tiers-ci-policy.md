**Title:** Validation tiers and CI marker policy for cpa-sim.

- **ADR ID:** ADR-0003
- **Status:** Proposed
- **Date:** 2026-02-16
- **Deciders:** @cpa-sim maintainers
- **Area:** testing
- **Related ecosystem ADRs:** ECO-0003
- **Tags:** ci, testing, reproducibility
- **Scope:** cpa-sim

### Context
`cpa-sim` contains both fast software-correctness checks and slower physics validation for free-space and fiber models. We need explicit marker policy so PR checks stay fast while preserving confidence in theoretical correctness.

### Decision
Adopt ECO-0003 marker-aligned validation tiers:

- **Tier 0 (PR-gated):** fast deterministic unit/integration checks.
  - Command: `python -m pytest -q -m "not slow and not physics" --durations=10`
- **Tier 1 (nightly/manual):** canonical theoretical physics regressions.
  - Command: `python -m pytest -q -m "physics" --durations=10`
- **Tier 2 (manual/report):** experimental comparisons with uncertainty accounting.

Required markers: `unit`, `integration`, `physics`, `slow`.

### Tolerance policy
- Tier 0 uses strict deterministic tolerances.
- Tier 1 stores metric-specific tolerances near fixture baselines.
- Tier 2 must document uncertainty sources and comparison methodology.

### Consequences
- **Positive:** faster PR iteration with explicit deeper validation paths.
- **Negative:** marker hygiene must be maintained to prevent slow-test leakage into PR gates.
- **Implementation follow-up:** audit existing tests and add missing markers.

### Validation
- CI commands map to tier policy.
- Periodic marker audit in PR review.
- Determinism checks enforce stable seeded outputs.

### References
- `cpa-architecture/docs/adr/ECO-0003-validation-tiers-ci-policy.md`
