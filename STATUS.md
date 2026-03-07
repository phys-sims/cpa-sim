# Project Status (cpa-sim)

> **Source of truth:** Update this file whenever behavior, tests, schemas, or canonical examples change.

## Last updated
- Date: 2026-03-07
- By: @openai-codex
- Note: Keep this section capped at the 5 most recent scope entries.
- Scope: Implemented the generic tuning engine with typed `TuneConfig`/optimizer/execution/output schemas, dot-path → `phys_sims_utils.ml.ParameterSpace` conversion, a deterministic pipeline adapter returning `EvalResult`, a functional `cpa-sim tune run --config ...` CLI wiring (`OptimizationRunner`/`OptimizationLogger`/`CMAESStrategy`), best-config persistence plus optional best-point rerun, and new unit/integration coverage for parameter-space conversion and end-to-end tune CLI execution with artifact output.
- Scope: Added a unit marker to `tests/unit/test_tuning_imports.py` so marker hygiene enforcement passes for all `tests/unit/test_*.py` files and restored the required fast-gate pytest run to green.
- Scope: Hardened tuning dot-path patching to reject unknown intermediate/leaf keys by default (preventing silent no-op typo paths during optimization), added explicit `create_missing` opt-in behavior, and added unit coverage for accepted/rejected path updates.
- Scope: Integrated free-space `TreacyGratingStage` with policy-driven `run_with_auto_window` reruns (phase re-evaluated per padded grid), persisted auto-window provenance events in `state.meta`, merged auto-window metrics into stage metrics, and added unit coverage for enabled/disabled behavior across both `PhaseOnlyDispersionCfg` and `TreacyGratingPairCfg`.
- Scope: Added policy-driven auto-window helpers in `physics/windowing` (`auto_window_enabled_for_stage`, `_next_n_samples`, `run_with_auto_window`) for free-space-only run→diagnose→pad→rerun control with deterministic event/metrics reporting, plus unit coverage for no-rerun behavior when edge energy already satisfies threshold.
- Scope: Added a minimal tuning scaffold under `cpa_sim.tuning` (schema, parameter-space patching, policy adapter, objective placeholder, and tune CLI module), wired a new `cpa-sim tune run` placeholder subcommand into the main CLI, kept the `ml` extra aligned to `phys-sims-utils[ml]` (without redundant direct CMA dependency), and added integration/unit coverage for tune help, tune placeholder defaults, and tuning package imports.
- Scope: Refactored example-script integration coverage into a single parameterized matrix test that validates run-example execution, artifact-key schemas, and non-empty SVG artifact files; narrowed per-example tests to focused contracts (SPM summary JSON structure and WUST stage-derived artifact naming) while removing duplicated generic artifact assertions.
- Scope: Enforced FiberAmpWrap nonlinearity inputs as an XOR contract (`gamma_1_per_w_m` vs `n2_m2_per_w`+`aeff_m2`), added unit validation coverage for accepted/rejected combinations, and updated the SPM-after-amp example/docs to showcase n2+Aeff inputs instead of direct gamma.
- Scope: Added `cpa_sim.reporting.pipeline_run.run_pipeline_with_plot_policy` as a shared script-facing run helper that applies canonical plotting policy and returns canonical metrics/artifact payloads; refactored CLI plus the WUST fiber, SPM-after-amp, and dispersive-wave showcase examples to consume canonical stage plot artifacts instead of duplicating standard line plotting; isolated docs-only render intermediates under `docs_rendering/runtime_stage_plots`; and added integration coverage asserting example artifact keys and no duplicate script-local standard plotting calls.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-03-07 | Passed; pre-commit still reports only a deprecation warning for `default_stages`. |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-03-07 | Success: no issues found in 62 source files. |
| Pytest fast (required gate) | `python -m pytest -q -m "not slow and not physics" --durations=10` | ✅ | 2026-03-07 | Passed (139 tests, 11 deselected). |
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
| `configs/examples/autocorr_input_demo.yaml` | ✅ | ✅ | Demonstrates `avg_power_w` normalization with `intensity_autocorr_fwhm_fs` input; docs warn to provide raw autocorrelation widths only (avoid double conversion). |

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
