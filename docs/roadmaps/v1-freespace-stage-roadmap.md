# FreeSpaceStage: Treacy grating‑pair backend — implementation roadmap

> **Stability:** This file is meant to be **frequently updated** by agents.
> **Source of truth:** Update this checklist whenever behavior, tests, schemas, or validation fixtures change.
> **IMPORTANT:** Always write **absolute dates** (YYYY-MM-DD) to avoid “today/yesterday” mistakes.

## Status header (keep current)
- Last updated: 2026-02-17
- Updated by: @openai-codex
- Target milestone: v1 Treacy compressor parity with LaserCalculator

---

## 0) Agent rules of engagement (to prevent repo damage)
- Do not change unit conventions (ADR-0001).
- Do not re-implement phys-pipeline primitives (ADR-0005).
- When migrating configs, preserve back-compat and add warnings.
- Keep tests fast; mark slow physics tests explicitly if added later.

---

## 1) Discovery checklist (agent must do first)
- [x] Locate `FreeSpaceCfg` definition (migrated to discriminated union in `src/cpa_sim/models/config.py`).
- [x] Locate `FreeSpaceStage` implementation/dispatch (`src/cpa_sim/stages/free_space/treacy_grating.py`, `src/cpa_sim/stages/registry.py`).
- [x] Identify where pulse spectrum and frequency grid live in state (`LaserState.pulse.field_w`, `LaserState.pulse.grid.w`).
- [x] Identify existing test patterns and fixtures layout and added `tests/fixtures/treacy_grating_pair_golden.json`.

**Exit criteria:** agent can name the exact module paths and the canonical way to access `ω` and `E(ω)` in the simulation state.

---

## 2) Config/schema migration (replace placeholder safely)
### Tasks
- [x] Replace placeholder `FreeSpaceCfg(kind="treacy_grating", gdd_fs2=...)` with a discriminated union:
  - `TreacyGratingPairCfg(kind="treacy_grating_pair", ...)`
  - `PhaseOnlyDispersionCfg(kind="phase_only_dispersion", ...)`
- [x] Add a `model_validator(mode="before")` that maps legacy shapes:
  - legacy `kind="treacy_grating"` + `gdd_fs2` → `phase_only_dispersion`
- [x] Add a deprecation warning for legacy config usage.
- [ ] Update `PipelineConfig` defaults:
  - `compressor` default should be `treacy_grating_pair` (geometry-based) or remain legacy but documented
  - `stretcher` may remain phase-only until Martinez exists

### Tests
- [ ] `test_legacy_freespace_cfg_migrates()`:
  - parses legacy dict
  - yields `PhaseOnlyDispersionCfg`
  - asserts deprecation warning emitted

**Exit criteria:** configs parse deterministically; mypy passes; legacy configs still run.

---

## 3) Implement geometry backend (coefficients only)
### Tasks
- [x] Create backend module (or extend existing) for `treacy_grating_pair`:
  - conversions: nm→um; lpmm→period_um; deg→rad
  - compute `GDD` and `TOD` using the reference formulas
  - domain checks with clear errors
  - record scalar diagnostics (`θL`, `θD`, `omega0`)
- [x] Ensure outputs are in internal units (`gdd_fs2`, `tod_fs3`)

### Tests (fast unit)
- [x] `test_unit_conversions()`:
  - period_um = 1000/lpmm
  - lambda_um = nm*1e-3
- [x] `test_invalid_order_raises()`:
  - choose inputs that make `asin` invalid; assert ValueError message contains key numbers
- [x] `test_sign_sanity()` (weak sanity):
  - pick a typical case; assert `gdd_fs2 < 0` (for default N=2,m=-1 geometry)
  (This is a sanity check; golden tests are the real guardrail.)

**Exit criteria:** backend computes stable coefficients; errors are clean; diagnostics present.

---

## 4) Apply phase to pulse (phase-only propagation)
### Tasks
- [x] Implement `apply_to_pulse=True` path:
  - identify canonical `ω` grid in `rad/fs`
  - compute `φ(ω)` Taylor expansion about `ω0`
  - multiply spectrum by `exp(iφ)`
- [x] Keep `apply_to_pulse=False` functional (metrics still computed, state unchanged)

### Tests (invariants)
- [x] `test_phase_only_preserves_spectral_magnitude()`:
  - run stage
  - assert `abs(Ew_out)` equals `abs(Ew_in)` within tolerance
- [x] `test_phase_only_preserves_energy()`:
  - compute energy via ADR-0001 rule (envelope in sqrt(W))
  - assert conserved within tolerance
- [x] `test_apply_to_pulse_false_is_noop()`

**Exit criteria:** stage is provably phase-only; energy and magnitude invariants pass.

---

## 5) Golden parity vs LaserCalculator (the real acceptance test)
### Files
- [x] Add fixture file: `tests/fixtures/treacy_grating_pair_golden.json`

### Fixture schema (agent creates structure; human can fill numbers)
Each entry:
```json
{
  "name": "case_01",
  "line_density_lpmm": 1200.0,
  "incidence_angle_deg": 35.0,
  "separation_um": 100000.0,
  "wavelength_nm": 1030.0,
  "diffraction_order": -1,
  "n_passes": 2,
  "expect_gdd_fs2": 0.0,
  "expect_tod_fs3": 0.0,
  "expect_diffraction_angle_deg": 0.0
}
```

### Tasks
- [x] Agent creates the fixture file with **10–15 cases** and `expect_*` values set to `null` placeholders.
- [ ] Human fills `expect_*` values from the calculator outputs (see “What the human must provide” section below).
- [x] Add test: `test_treacy_matches_golden()`:
  - load cases
  - compute metrics-only (skip applying to pulse for speed)
  - compare `gdd_fs2` and `tod_fs3` to expected with tight tolerances
  - optionally compare `diffraction_angle_deg`

### Tolerances
- [ ] Define constants in the test file:
  - `RTOL = 1e-10`
  - `ATOL_GDD = 1e-6` (fs^2)
  - `ATOL_TOD = 1e-3` (fs^3)  (adjust if reference rounds heavily)

**Exit criteria:** all golden cases match; this blocks sign-convention regressions.

---

## 6) Integration test (tiny end-to-end)
### Tasks
- [x] Add a tiny pipeline config: laser → compressor → metrics
- [x] Run pipeline once, assert metrics keys exist and are finite
- [ ] Assert invariants still hold (energy conserved)

**Exit criteria:** stage works inside the real pipeline, not just unit-tested in isolation.

---

## 7) Documentation and UX polish
- [ ] Update main docs/readme to explain:
  - what `treacy_grating_pair` does
  - units and required inputs
  - how to regenerate golden fixtures
- [ ] Add an example config snippet showing a realistic 1560 nm compressor

---

## 8) CI gates (must stay green)
- [ ] `python -m pytest -q`
- [ ] `python -m mypy src`
- [ ] `python -m pre_commit run -a`

---

## What the human must provide (minimal but necessary)
### 1) Golden reference numbers (yes, you should provide these)
To truly claim “matches LaserCalculator,” you need **expected** values from the calculator.
An agent can create the fixture structure and tests, but without reliable web access (or if you don’t want automated scraping), you should manually copy outputs.

**Best workflow:**
1. Agent creates `tests/fixtures/treacy_grating_pair_golden.json` with 10–15 cases and placeholders.
2. You fill:
   - `expect_gdd_fs2`
   - `expect_tod_fs3`
   - (optional) `expect_diffraction_angle_deg`
3. Commit the filled fixture; agent re-runs tests and tightens tolerances if needed.

If you *do* allow the agent browser access, it can populate the numbers itself, but that’s riskier (site changes, scraping fragility, ToS ambiguity). Manual copy is the robust approach.

### 2) Confirm the “separation” meaning you want
The reference uses “physical distance between gratings.” If your lab practice uses a different effective distance definition (e.g., projection along beam path), decide now and keep it consistent.

### 3) Confirm where ω-grid and spectrum live in your state
An agent can discover this by reading the repo, but if you want minimal supervision, provide:
- the exact attribute names for `omega_rad_per_fs` (or equivalent)
- whether you store spectral field as `Ew` and/or time field `Et`
- the canonical energy computation helper (if one exists)

If you don’t provide this, the agent can still infer it, but you’ll spend time reviewing.

---

## Quick “numbers don’t match” triage (agent checklist)
If golden mismatch occurs, it is almost always:
- [ ] `n_passes` missing factor 2
- [ ] `diffraction_order` sign convention mismatch (`m=-1`)
- [ ] unit conversion error (lpmm→period; nm→um)
- [ ] wrong diffraction angle formula (transmission sign convention)

Golden tests + recording `diffraction_angle_deg` make this obvious.
