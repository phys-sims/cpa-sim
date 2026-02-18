# Project Status (cpa-sim)

> **Source of truth:** Update this file whenever behavior, tests, schemas, or canonical examples change.

## Last updated
- Date: 2026-02-18
- By: @openai-codex
- Scope: Refactored toy amp A/B example scripts to share one canonical laser seed config, made A/B comparison metrics schema stage-name-agnostic, and strengthened integration coverage for non-brittle comparison outputs.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-02-18 | Passed; pre-commit reported only a deprecation warning for `default_stages`. |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-02-18 | Success: no issues found in 37 source files. |
| Pytest fast (required gate) | `python -m pytest -q -m "not slow and not physics" --durations=10` | ✅ | 2026-02-18 | Passed after adding toy amp backend/tests. |
| Pytest physics (supplemental) | `python -m pytest -q -m physics --durations=10` | ⬜ | — | Not rerun in this change set. |
| Pytest slow (supplemental) | `python -m pytest -q -m slow --durations=10` | ⬜ | — |  |
| Pytest gnlse optional (supplemental) | `python -m pytest -q -m gnlse --durations=10` | ✅ | 2026-02-17 | 4 passed, 15 deselected (includes new example artifact test). |
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
| `configs/examples/basic_cpa.yaml` | ⬜ | ⬜ | Tiny grid, CI-friendly end-to-end smoke. |
| `configs/examples/gnlse_canonical.yaml` | ⬜ | ⬜ | Reproduces one upstream solver canonical example (pinned metrics). |
| `configs/examples/tracy_golden.yaml` | ⬜ | ⬜ | Free-space golden case with pinned metrics. |

---

## Roadmap checklist (v1 focus)

### Stages (end-to-end chain)
- [x] PulseInitStage (laser_gen analytic backend)
- [x] FreeSpaceStage: `treacy_grating` backend (stretcher/compressor)
- [x] FiberStage: Strategy B `FiberStageCfg(physics, numerics)` with `toy_phase` and `wust_gnlse` backends
- [x] AmpStage: `simple_gain` and `toy_fiber_amp` backends
- [x] MetricsStage (energy, FWHM, bandwidth, B-integral proxy)
- [ ] Report/Validation schema (tiered validation records)

### Backends + adapters
- [x] External solver adapter isolated (no scattered third-party calls)
- [x] Unit normalization metadata + grid invariant tests

### QA / determinism
- [x] Determinism tests (same config + seed)
- [x] Integration smoke test (fast, CI)
- [ ] Physics golden tests (free-space + fiber)

### Docs / ADRs
- [x] ADR-0001 conventions (units, FFT, sign)
- [x] ADR-0002 canonical result schema contract
- [x] ADR-0003 validation tiers + CI policy
- [x] ADR-0004 stage/domain boundaries (laser, free-space, fiber, amp)
- [x] ADR-0005 phys-pipeline contract adoption

### Release readiness
- [ ] README quickstart + one runnable config
- [x] CLI stable (`cpa-sim run ...`)
- [ ] CHANGELOG + versioning policy
- [ ] PyPI build passes (`python -m build`)

---

## Known issues
- None tracked yet.

---

## Next actions
- [x] Run initial CI commands locally and populate the CI health checklist rows.
- [ ] Add minimal canonical configs under `configs/examples/`.
- [x] Land first end-to-end smoke test and record runtimes here.
