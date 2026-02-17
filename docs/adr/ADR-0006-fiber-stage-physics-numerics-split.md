**Title:** Split FiberStage config into stable physics and backend numerics.

- **ADR ID:** ADR-0006
- **Status:** Proposed
- **Date:** 2026-02-16
- **Deciders:** @RyaanLari
- **Area:** cpa-sim
- **Related:** docs/agent/fiber-stage-context.md, docs/agent/fiber-stage-roadmap.md
- **Tags:** api, data-model, performance, testing, reproducibility

### Context
- **Problem statement.** `cpa-sim` needs a `FiberStage` now, and the fastest credible backend is WUST-FOG's `gnlse` (Python). The project also plans to add an in-house GNLS solver (`glnse-sim`) with variable fidelity and ML-native workflows. If a single backend's API/units define the public config now, future backends will likely force lock-in or breaking changes.
- **In/Out of scope.**
  - In scope: the public shape of `FiberStageCfg`; separation of physical parameters from solver numerics; backend selection boundary inside `FiberStage`.
  - Out of scope: implementing the in-house GNLS solver; adding new fiber physics beyond core GNLS effects in this ADR.
- **Constraints.**
  - Reproducibility: deterministic configs, pinned versions where possible, explicit backend/version provenance.
  - Correctness: explicit normalization (prefer `sqrt(W)`), explicit units, explicit grid policy.
  - Maintainability: avoid public API churn when introducing future backends.
  - Delivery: allow the WUST-FOG backend to ship quickly behind a stable interface.

### Options Considered

**Option A — Backend-shaped public config (mirror WUST-FOG setup)**
- **Description:** Model `FiberStageCfg` directly after WUST-FOG `GNLSESetup` fields (`resolution`, `time_window_ps`, `wavelength_nm`, `z_saves`, tolerance knobs, Taylor `betas`, etc.).
- **Impact areas:** public API, units/conventions, docs/tests coupled to upstream solver choices.
- **Pros:**
  - Fastest initial implementation.
  - Minimal adapter code initially.
- **Cons:**
  - Strong backend lock-in and solver-specific public schema.
  - Future backend support likely causes schema bloat or migrations.
- **Risks / Unknowns:**
  - Hidden normalization/unit mismatches can introduce physically invalid results.
- **Perf/Resource cost:** low now; uncertain long-term due to compatibility drag.
- **Operational complexity:** low now, high later.
- **Dependencies / Externalities:** long-term API coupling to WUST-FOG release behavior.

**Option B — Stable `physics` + backend-specific `numerics` (Strategy B)**
- **Description:**
  - `FiberPhysicsCfg`: stable physical meaning (length, loss, dispersion, gamma, effect toggles).
  - `FiberNumericsCfg`: discriminated union by `backend` (`toy_phase`, `wust_gnlse`, later `inhouse_gnlse`) for solver/grid knobs.
  - Backend adapters map `(LaserState, physics, numerics)` to solver calls and map outputs back.
- **Impact areas:** config model, backend adapters, cross-backend validation contracts.
- **Pros:**
  - Stable public physics API across backend evolution.
  - Better ML/testbench ergonomics via consistent physics feature space.
  - Supports incremental backend additions without public schema rewrites.
- **Cons:**
  - Requires adapter layer and disciplined conversion handling.
- **Risks / Unknowns:**
  - Translation bugs unless contract tests pin invariants and conventions.
- **Perf/Resource cost:** negligible adapter overhead.
- **Operational complexity:** moderate now, lower long-term.
- **Dependencies / Externalities:** isolates optional solver dependency to backend module.

**Option C — Backend union as full public config**
- **Description:** `FiberStageCfg = WustGnlseCfg | InHouseGnlseCfg | ...`, with each variant containing both physics and numerics.
- **Impact areas:** typing, public API growth, docs burden.
- **Pros:**
  - Explicit per-backend fields.
- **Cons:**
  - Duplicates shared physics concepts across variants.
  - Higher schema churn and weaker cross-backend ergonomics.
- **Risks / Unknowns:**
  - Long-term migration fatigue as backends accumulate.
- **Perf/Resource cost:** similar runtime to Option B.
- **Operational complexity:** medium now, high later.

**Option D — Internal plugin backend registry**
- **Description:** Internal protocol like `FiberBackend.run(state, physics, numerics) -> StageResult`, with dispatch by backend key.
- **Impact areas:** architecture boundary, optional dependencies, backend isolation.
- **Pros:**
  - Clean backend isolation and optional import boundaries.
  - Better A/B backend comparison and contract testing.
- **Cons:**
  - Requires upfront interface discipline.
- **Risks / Unknowns:**
  - Potential orchestration/backend leakage if boundaries are not enforced.
- **Perf/Resource cost:** negligible.
- **Operational complexity:** low long-term.

### Decision
- **Chosen option:** Option B for public config, implemented with Option D as the internal backend boundary.
- **Trade-offs:** accept a translation layer plus adapter tests to avoid lock-in and repeated schema migrations.
- **Scope of adoption:** applies to all `cpa-sim` FiberStage backends; prototype shortcuts are allowed only for short-lived spikes and must not become stable public config.

### Consequences
- **Positive:**
  - Stable physics-facing config independent of solver implementation.
  - Localized optional dependency handling for WUST-FOG `gnlse`.
  - Clear path to add `inhouse_gnlse` without breaking public physics config.
- **Negative / Mitigations:**
  - Adapter conversion mismatches (units/FFT/signs) can occur.
    - Mitigation: central conversion utilities; invariant integration tests (SPM-only, GVD-only); explicit normalization metadata.
  - Ambiguity of what belongs in physics vs numerics.
    - Mitigation: solver tolerances, save strategy, and grid policy are numerics; physical coefficients/toggles are physics.
- **Migration plan:**
  1) Introduce `FiberStageCfg(physics, numerics)` and temporary compatibility shim.
  2) Add `backend="wust_gnlse"` numerics config and lazy optional imports.
  3) Keep a fast baseline via `backend="toy_phase"`.
  4) Add `backend="inhouse_gnlse"` later without changing `FiberPhysicsCfg`.
- **Test strategy:**
  - Unit: discriminated-union validation, grid policy checks, no silent resampling unless explicitly allowed.
  - Integration: SPM-only and GVD-only trend tests; finite outputs with optional Raman toggle.
  - Success thresholds: no NaN/Inf, expected monotonic trends, lossless energy conservation within tolerance.
- **Monitoring & Telemetry:** record backend name/version, grid policy, energy in/out, spectral RMS in/out in stage provenance.
- **Documentation:** maintain `docs/agent/fiber-stage-context.md` (spec) and `docs/agent/fiber-stage-roadmap.md` (execution checklist).

### Alternatives Considered (but not chosen)
- Option A rejected due to lock-in risk.
- Option C rejected due to schema growth and duplicated physics semantics.

### Open Questions
- Should `PulseState.field_t` be standardized to `sqrt(W)` immediately, or bridged temporarily?
- What is the canonical FFT convention for `PulseState.field_w` across all stages?
- What long-term dispersion representation should extend beyond Taylor betas (e.g., measured/interpolated curves)?

### References
- `docs/agent/fiber-stage-context.md`
- `docs/agent/fiber-stage-roadmap.md`
- WUST-FOG `gnlse` documentation/repository

### Changelog
- 2026-02-16 — Proposed by @RyaanLari
