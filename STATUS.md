# Project Status (cpa-sim)

> **Source of truth:** Update this file whenever behavior, tests, schemas, or canonical examples change.

## Last updated
- Date: 2026-02-27
- By: @openai-codex
- Scope: Updated CI workflow policy alignment: required PR gate now runs pre-commit, mypy on `src`, and fast pytest marker gate; moved physics and optional gnlse checks to isolated workflows.
- Scope: Updated the WUST-GNLSE fiber example (script + canonical YAML) to a 1550 nm, 1 ps pulse with explicit Kerr nonlinearity and Blow-Wood Raman response to better demonstrate nonlinear evolution.
- Scope: Updated analytic laser pulse generation so gaussian and sech2 shapes are defined from intensity-domain formulas with width_fs as intensity FWHM, added explicit PulseSpec shape/width semantics, and added unit coverage for FWHM behavior.
- Scope: Added pulse sampling-policy helpers (minimum points per FWHM plus optional Nyquist/window checks), tightened toy amp example laser-grid construction to target denser short-pulse sampling, and documented rationale in the toy A/B gallery doc.
- Scope: Audited stage metric naming under src/cpa_sim/stages, enforced explicit energy/power suffixes for WUST-GNLSE fiber backend metrics with fs→s Joule conversion, and added unit tests for metric-key suffix policy across laser/free-space/fiber/amp stages.
- Scope: Added new canonical physics regressions for analytic laser TBP/FWHM targets, Treacy free-space geometry + chirp-sign behavior, and WUST-GNLSE fiber summary metrics; expanded ADR-0003 with explicit canonical cases and tolerances.
- Scope: Added a laser measurement mapping module to convert vendor pulsewidth measurements (including autocorrelation deconvolution and uncertainty bounds) into simulation width, wired this mapping into the toy amp A/B example, and persisted mapping assumptions into per-run metadata/artifacts for auditability.
- Scope: Added a minimal observable contract model (`cpa.observables.v0.1`) that separates latent field state from measured observables (FWHM, autocorrelation FWHM, spectral RMS width), emitted observable metadata from the metrics stage, extended ADR-0001/0002 with the contract, and updated example scripts for observable-aware reporting.
- Scope: Added canonical YAML configs under `configs/examples/` (`basic_cpa`, `tracy_golden`, and `gnlse_canonical`), wired integration tests to load these files directly (including optional gnlse skip behavior), and updated README quickstart CLI commands accordingly.
- Scope: Defined canonical CLI output layout (`metrics.json`, `artifacts.json`, `stage_plots/`, optional `state_final.npz`), added legacy filename deprecation fallback, documented migration in README + ADR-0008, and expanded CLI integration tests for exact filenames/required keys.
- Scope: Added lightweight reporting package (`cpa_sim.reporting`) with `cpa.validation_report.v1` schema models, report builders/markdown renderer, CLI emission of `report.json` + `report.md`, and unit/integration test coverage for report serialization and output creation.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-02-21 | Passed; pre-commit reported only a deprecation warning for `default_stages`. |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-02-21 | Success: no issues found in 41 source files. |
| Pytest fast (required gate) | `python -m pytest -q -m "not slow and not physics" --durations=10` | ✅ | 2026-02-21 | Passed, including new pulse sampling policy unit coverage. |
| Pytest physics (nightly/manual) | `python -m pytest -q -m physics --durations=10` | ✅ | 2026-02-21 | Runs in `.github/workflows/physics.yml` (manual + nightly), not in required PR gate. |
| Pytest slow (supplemental) | `python -m pytest -q -m slow --durations=10` | ⬜ | — |  |
| Pytest gnlse optional (isolated/non-blocking) | `python -m pytest -q -m gnlse --durations=10` | ✅ | 2026-02-17 | Runs only in `.github/workflows/gnlse-optional.yml`; keep non-blocking unless branch protection intentionally requires it. |
| Pip editable install with extras (supplemental) | `pip install -e .[dev,gnlse]` | ⚠️ | 2026-02-17 | Failed in this environment due proxy/network restrictions when resolving build dependencies. |

---

## Test suites (definitions, runtimes, slowest tests)

Fill these in after first green run; keep them current.

| Suite | Definition | Typical runtime | Slowest tests (top 3) | Last measured | Notes |
| --- | --- | --- | --- | --- | --- |
| Fast | `-m "not slow and not physics" --durations=10` | — | — | — | PR gate |
| Physics | `-m physics --durations=10` | — | — | — | Canonical solver comparisons |
| Slow | `-m slow --durations=10` | — | — | — | Large grids / long fibers |
| Full | `-m "slow or physics or (not slow and not physics)" --durations=10` | — | — | — |  |

---

## Contract status (spec/result)

### Config / result schemas
- Config schema (planned): `cpa_config.schema.v0.1.json`
- Result schema (planned): `cpa_result.schema.v0.1.json`
- Pydantic models (planned): `cpa_sim/models/*`

> If schemas are not implemented yet, track “planned” until landed, then pin versions here.

### Canonical example configs (contract validation + runtime)

| Example | Config validate | Runtime validate | Notes |
| --- | --- | --- | --- |
| `configs/examples/basic_cpa.yaml` | ✅ | ✅ | Tiny grid, CI-friendly end-to-end smoke; validated via integration config-loading test. |
| `configs/examples/gnlse_canonical.yaml` | ✅ | ✅ | Fiber canonical config runs in integration when `gnlse` is installed; test uses optional dependency guard. |
| `configs/examples/tracy_golden.yaml` | ✅ | ✅ | Free-space canonical config validated by integration load/run test with Treacy metrics assertions. |

---

## Roadmap checklist (v1 focus)

### Stages (end-to-end chain)
- [x] PulseInitStage (laser_gen analytic backend)
- [x] FreeSpaceStage: `treacy_grating` backend (stretcher/compressor)
- [x] FiberStage: Strategy B `FiberStageCfg(physics, numerics)` with `toy_phase` and `wust_gnlse` backends
- [x] AmpStage: `simple_gain` and `toy_fiber_amp` backends
- [x] MetricsStage (energy, FWHM, bandwidth, B-integral proxy)
- [x] Report/Validation schema (tiered validation records)

### Backends + adapters
- [x] External solver adapter isolated (no scattered third-party calls)
- [x] Unit normalization metadata + grid invariant tests

### QA / determinism
- [x] Determinism tests (same config + seed)
- [x] Integration smoke test (fast, CI)
- [x] Physics golden tests (free-space + fiber)

### Docs / ADRs
- [x] ADR-0001 conventions (units, FFT, sign)
- [x] ADR-0002 canonical result schema contract
- [x] ADR-0003 validation tiers + CI policy
- [x] ADR-0004 stage/domain boundaries (laser, free-space, fiber, amp)
- [x] ADR-0005 phys-pipeline contract adoption
- [x] ADR-0008 canonical output layout + migration behavior

### Release readiness
- [x] README quickstart + one runnable config
- [x] CLI stable (`cpa-sim run ...`)
- [ ] CHANGELOG + versioning policy
- [ ] PyPI build passes (`python -m build`)

---

## Known issues
- None tracked yet.

---

## Next actions
- [x] Run initial CI commands locally and populate the CI health checklist rows.
- [x] Add minimal canonical configs under `configs/examples/`.
- [x] Land first end-to-end smoke test and record runtimes here.
