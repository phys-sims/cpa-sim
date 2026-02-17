# Fiber Stage Roadmap (Strategy B + WUST‑FOG gnlse backend)

**Last updated:** 2026-02-16
**Depends on:** `docs/agent/fiber-stage-context.md` (read it first)

## Why this is a separate file
This roadmap is expected to change frequently (checkboxes, status, notes). Keeping it separate prevents churn in the stable spec doc.

---

## Phase 0 — Preflight (repo sanity)

- [x] Confirm where current fiber stub lives (e.g., `src/cpa_sim/stages/fiber/glnse_wrap.py`)
- [x] Identify canonical FFT helpers and PulseGrid definitions (avoid duplicating FFT conventions)
- [x] Confirm `LaserState` contains `pulse` and `beam` (or implement minimal BeamState placeholder)

**Tests**
- [x] `pytest -q` baseline passes before changes

---

## Phase 1 — Implement Strategy B configs

- [x] Add `FiberStageCfg(physics, numerics)` and replace/alias old `FiberCfg`
- [x] Implement `FiberPhysicsCfg`, `DispersionCfg` union, `RamanCfg`
- [x] Implement `FiberNumericsCfg` union:
  - [x] `ToyPhaseNumericsCfg`
  - [x] `WustGnlseNumericsCfg`

**Tests**
- [x] Unit test: config discriminators work
- [x] Unit test: missing required physics fields raises clean errors

---

## Phase 2 — FiberStage orchestrator + backend protocol

- [x] Create `fiber_stage.py` that:
  - [x] validates state invariants (uniform grid, metadata)
  - [x] dispatches to backend by `cfg.numerics.backend`
  - [x] returns `StageResult` with artifacts/metrics

- [x] Create backend modules:
  - [x] `backends/toy_phase.py` (move existing stub logic here)
  - [x] `backends/wust_gnlse.py` (new)

**Tests**
- [x] Unit test: dispatch selects correct backend
- [x] Unit test: toy backend preserves BeamState unchanged

---

## Phase 3 — Grid + units utilities

- [x] Add `utils/units.py`:
  - [x] fs↔ps conversions
  - [ ] nm↔(if needed later)

- [x] Add `utils/grid.py`:
  - [x] uniform spacing check
  - [x] prime factor warning helper
  - [x] resampling helper (complex interpolation)

**Tests**
- [x] Unit test: jittered grid triggers error
- [x] Unit test: resampling changes N only when allowed

---

## Phase 4 — Implement WUST‑FOG backend (core)

- [x] Lazy-import `gnlse`
- [x] Build `GNLSESetup` from `LaserState` + `FiberPhysicsCfg` + `WustGnlseNumericsCfg`
- [x] Map dispersion:
  - [x] Taylor -> `DispersionFiberFromTaylor(loss, betas)`
  - [x] Interpolation -> `DispersionFiberFromInterpolation(...)`
- [x] Map Raman string -> function
- [x] Run solver
- [x] Convert output back into `LaserState`:
  - [x] `pulse.field_t`
  - [x] `pulse.intensity_t`
  - [x] `pulse.field_w` + `pulse.spectrum_w` (prefer project FFT helper)
- [x] Attach provenance artifacts and key metrics

**Tests**
- [x] Unit test: setup fields populated with correct units
- [x] Unit test: run fails with clear error if `gnlse` missing (and message suggests extras)

---

## Phase 5 — Optional dependency packaging

- [x] Add extras: `cpa-sim[gnlse]` in `pyproject.toml`
- [x] Document install in README or docs page:
  - [x] “pip install -e '.[gnlse]'”
- [ ] CI plan:
  - [ ] normal job runs unit tests without gnlse
  - [ ] optional job installs FFTW + `.[gnlse]` and runs integration tests

**Tests**
- [ ] `pip install -e '.[gnlse]'` works locally
- [ ] Optional CI job installs `libfftw3-dev` (Ubuntu) and passes

---

## Phase 6 — Integration tests (gnlse installed)

Mark these tests, e.g. `@pytest.mark.gnlse` and skip if dependency missing.

- [x] SPM-only case:
  - [x] loss=0, dispersion=None, gamma>0
  - [x] assert energy ~ conserved
  - [x] assert spectral RMS increases

- [x] GVD-only case:
  - [x] gamma=0, beta2!=0
  - [x] assert temporal RMS increases

- [ ] Raman toggle:
  - [ ] enable one model and confirm finite output and run completion

**Tests**
- [ ] `pytest -q -m gnlse` passes in gnlse-enabled environment

---

## Phase 7 — Docs & examples (“wow factor” optional)

- [ ] Add a small runnable example script:
  - [ ] create input pulse
  - [ ] run fiber stage with WUST gnlse
  - [ ] save a couple plots (time + spectrum)
- [ ] Update docs to describe:
  - [ ] config fields and units
  - [ ] backend selection
  - [ ] normalization expectations

**Tests**
- [ ] Example runs end-to-end without manual edits

---
