# Project Status (cpa-sim)

> **Source of truth:** Update this file whenever behavior, tests, schemas, or canonical examples change.

## Last updated
- Date: 2026-02-27
- By: @openai-codex
- Scope: Updated pulse sampling adequacy checks to always use resolved intensity FWHM via `resolve_intensity_fwhm_fs` (including autocorrelation deconvolution), refreshed sampling warning/error wording, and added unit/integration tests for autocorrelation-only width handling plus CLI validation messaging for explicitly conflicting width inputs.
- Scope: Updated `AnalyticLaserGenStage` to resolve pulse normalization via `resolve_intensity_fwhm_fs` + `resolve_peak_power_w`, switched generation to effective intensity FWHM/peak power semantics, and added audit metadata/metrics (`laser.intensity_fwhm_fs`, `laser.peak_power_w`, `laser.pulse_energy_j`, `laser.avg_power_w`, autocorr input echo).
- Scope: Added unit tests covering analytic laser energy closure from `avg_power_w`, peak-power consistency for gaussian/sech2, and autocorrelation-width deconvolution behavior; preserved legacy amplitude compatibility (with deprecation warnings).
- Scope: Extended `PulseSpec` with user-friendly pulse normalization inputs (`avg_power_w`, `pulse_energy_j`, `peak_power_w`), optional intensity-autocorrelation width input, explicit mutual-exclusion validation for normalization/width inputs using explicit field-set detection, and deprecation schema/warning behavior for explicit `amplitude`; added focused unit tests for conflicts, warning emission, and schema deprecation metadata.
- Scope: Removed the deprecated toy fiber amp A/B gallery example doc, switched the canonical 1560 nm chain example to use the `fiber_amp_wrap` amplifier backend, and configured canonical fiber/amp fiber stages to run on the WUST-FOG `wust_gnlse` backend with docs updated for the optional dependency.
- Scope: Updated CI workflow policy alignment: required PR gate now runs pre-commit, mypy on `src`, and fast pytest marker gate; moved physics and optional gnlse checks to isolated workflows.
- Scope: Reworked `FiberAmpWrapStage` to compute net gain from input pulse energy/rep-rate, map to effective+intrinsic distributed loss, delegate propagation strictly through `FiberStage`, and emit wrapper gain/loss/energy/power metrics with explicit error handling for invalid rep rate/power/length cases; updated unit coverage accordingly.
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
- Scope: Relaxed `FiberPhysicsCfg.loss_db_per_m` validation to allow finite negative values as distributed gain semantics for `fiber_amp_wrap`, updated fiber docs wording, and added focused unit coverage for +/0/- acceptance.
- Scope: Added an optional integration regression for `FiberAmpWrapStage` with the `wust_gnlse` backend in gain/loss-only mode (`gamma=0`, zero Taylor dispersion), asserting `amp.power_out_avg_w` tracks the requested power target within a loose relative tolerance.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-02-27 | Passed; pre-commit reported only a deprecation warning for `default_stages`. |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-02-27 | Success: no issues found in 44 source files. |
| Pytest fast (required gate) | `python -m pytest -q -m "not slow and not physics" --durations=10` | ✅ | 2026-02-27 | Passed (81 tests), including analytic laser normalization/deconvolution coverage. |
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
- [x] AmpStage: `simple_gain` and `fiber_amp_wrap` backends
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
