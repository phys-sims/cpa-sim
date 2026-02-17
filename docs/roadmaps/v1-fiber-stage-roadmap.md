# Fiber Stage Roadmap (Strategy B + WUST‑FOG gnlse backend)

**Last updated:** 2026-02-16  
**Depends on:** `docs/agent/fiber-stage-context.md` (read it first)

## Why this is a separate file
This roadmap is expected to change frequently (checkboxes, status, notes). Keeping it separate prevents churn in the stable spec doc.

---

## Phase 0 — Preflight (repo sanity)

- [ ] Confirm where current fiber stub lives (e.g., `src/cpa_sim/stages/fiber/glnse_wrap.py`)
- [ ] Identify canonical FFT helpers and PulseGrid definitions (avoid duplicating FFT conventions)
- [ ] Confirm `LaserState` contains `pulse` and `beam` (or implement minimal BeamState placeholder)

**Tests**
- [ ] `pytest -q` baseline passes before changes

---

## Phase 1 — Implement Strategy B configs

- [ ] Add `FiberStageCfg(physics, numerics)` and replace/alias old `FiberCfg`
- [ ] Implement `FiberPhysicsCfg`, `DispersionCfg` union, `RamanCfg`
- [ ] Implement `FiberNumericsCfg` union:
  - [ ] `ToyPhaseNumericsCfg`
  - [ ] `WustGnlseNumericsCfg`

**Tests**
- [ ] Unit test: config discriminators work
- [ ] Unit test: missing required physics fields raises clean errors

---

## Phase 2 — FiberStage orchestrator + backend protocol

- [ ] Create `fiber_stage.py` that:
  - [ ] validates state invariants (uniform grid, metadata)
  - [ ] dispatches to backend by `cfg.numerics.backend`
  - [ ] returns `StageResult` with artifacts/metrics

- [ ] Create backend modules:
  - [ ] `backends/toy_phase.py` (move existing stub logic here)
  - [ ] `backends/wust_gnlse.py` (new)

**Tests**
- [ ] Unit test: dispatch selects correct backend
- [ ] Unit test: toy backend preserves BeamState unchanged

---

## Phase 3 — Grid + units utilities

- [ ] Add `utils/units.py`:
  - [ ] fs↔ps conversions
  - [ ] nm↔(if needed later)

- [ ] Add `utils/grid.py`:
  - [ ] uniform spacing check
  - [ ] prime factor warning helper
  - [ ] resampling helper (complex interpolation)

**Tests**
- [ ] Unit test: jittered grid triggers error
- [ ] Unit test: resampling changes N only when allowed

---

## Phase 4 — Implement WUST‑FOG backend (core)

- [ ] Lazy-import `gnlse`
- [ ] Build `GNLSESetup` from `LaserState` + `FiberPhysicsCfg` + `WustGnlseNumericsCfg`
- [ ] Map dispersion:
  - [ ] Taylor -> `DispersionFiberFromTaylor(loss, betas)`
  - [ ] Interpolation -> `DispersionFiberFromInterpolation(...)`
- [ ] Map Raman string -> function
- [ ] Run solver
- [ ] Convert output back into `LaserState`:
  - [ ] `pulse.field_t`
  - [ ] `pulse.intensity_t`
  - [ ] `pulse.field_w` + `pulse.spectrum_w` (prefer project FFT helper)
- [ ] Attach provenance artifacts and key metrics

**Tests**
- [ ] Unit test: setup fields populated with correct units
- [ ] Unit test: run fails with clear error if `gnlse` missing (and message suggests extras)

---

## Phase 5 — Optional dependency packaging

- [ ] Add extras: `cpa-sim[gnlse]` in `pyproject.toml`
- [ ] Document install in README or docs page:
  - [ ] “pip install -e '.[gnlse]'”
- [ ] CI plan:
  - [ ] normal job runs unit tests without gnlse
  - [ ] optional job installs FFTW + `.[gnlse]` and runs integration tests

**Tests**
- [ ] `pip install -e '.[gnlse]'` works locally
- [ ] Optional CI job installs `libfftw3-dev` (Ubuntu) and passes

---

## Phase 6 — Integration tests (gnlse installed)

Mark these tests, e.g. `@pytest.mark.gnlse` and skip if dependency missing.

- [ ] SPM-only case:
  - [ ] loss=0, dispersion=None, gamma>0
  - [ ] assert energy ~ conserved
  - [ ] assert spectral RMS increases

- [ ] GVD-only case:
  - [ ] gamma=0, beta2!=0
  - [ ] assert temporal RMS increases

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
