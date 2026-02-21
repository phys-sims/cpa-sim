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


### Canonical Tier 1 cases and tolerances
Tier 1 (`@pytest.mark.physics`) currently pins the following canonical checks with tolerance blocks kept in each test module near fixtures:

- **Laser generator analytic pulse shapes** (`tests/physics/test_laser_gen_canonical.py`)
  - Gaussian and sech² transform-limited pulses
  - Pinned metrics: temporal intensity FWHM, time-bandwidth product (TBP)
  - Default tolerances: `fwhm_abs_fs=0.15`, `tbp_abs=0.015`
- **Free-space Treacy grating pair** (`tests/physics/test_free_space_treacy_canonical.py`)
  - Canonical geometry: 1200 lp/mm, 35°, 1030 nm, 100 mm separation, m=-1, 2 passes
  - Pinned metrics: GDD/TOD against golden reference plus chirp-sign compression behavior
  - Default tolerances: `gdd_abs_fs2=5e3`, `tod_abs_fs3=1e4`, compression margin `20 fs`
- **Fiber WUST-gnlse backend** (`tests/physics/test_fiber_wust_gnlse_canonical.py`)
  - Canonical SPM-focused run with zero-dispersion Taylor term
  - Pinned summary metrics: energy-ratio bounds, spectral bandwidth growth, phase-rotation proxy
  - Default tolerances: energy ratio in `[0.95, 1.05]`, bandwidth growth `>=1.02`, phase proxy in `[0.15, 0.25]`

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
