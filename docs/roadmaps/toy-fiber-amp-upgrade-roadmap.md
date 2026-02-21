# Toy Fiber Amplifier Upgrade Roadmap (v1-compatible, fast, deterministic)

**Last updated:** 2026-02-18
**Audience:** implementation agent + human reviewer
**Depends on:**
- `docs/adr/ADR-0001-conventions-units.md`
- `docs/adr/ADR-0002-result-schema-contract.md`
- `docs/adr/ADR-0003-validation-tiers-ci-policy.md`
- `docs/adr/ADR-0006-fiber-stage-physics-numerics-split.md`
- `docs/agent/fiber-stage-context.md`

---

## Purpose

Implement a **toy amplifier backend** inside the existing amp stage architecture that remains CI-friendly while adding:

- linear dispersion (`beta2`) support,
- Kerr SPM (`gamma`) support,
- distributed gain over length,
- optional distributed passive loss,
- deterministic metrics and tests,
- runnable A/B example docs:
  - **A:** direct seed → toy fiber amp (SPM visible)
  - **B:** CPA-style seed → stretcher → toy fiber amp → Treacy compressor (reduced nonlinear distortion during amp)

This roadmap intentionally aligns with current repository conventions (single stable state model, stage backends, validation tiers, ADR discipline).

---

## Non-goals / guardrails

- [ ] Do **not** present this as a full EDFA model.
- [ ] Do **not** add heavy runtime dependencies to core library.
- [ ] Do **not** break current `simple_gain` configs.
- [ ] Do **not** change public config/result shape without explicit migration notes + tests.
- [ ] Do **not** claim ASE, pump depletion, or wavelength-dependent gain unless implemented and validated.

---

## Design decisions to lock before coding

- [ ] **Matching criterion for Example B**: choose one and document everywhere:
  - option 1: match output energy,
  - option 2: match compressed peak power.
- [ ] Confirm pulse normalization used in amp stages:
  - if `|A(t)|^2` already treated as instantaneous power proxy, reuse consistently,
  - if ambiguous, add explicit note in docs and stage metrics labels.
- [ ] Confirm whether to implement first-order split-step or Strang split; default to Strang unless profiling says otherwise.

---

## Phase 0 — Preflight + ADR/status hygiene

- [ ] Read referenced ADRs + agent context docs before touching code.
- [ ] Add a short ADR amendment (or new ADR) for toy amp assumptions if conventions are newly introduced.
- [ ] Plan `STATUS.md` update entry for behavior/schema/test additions.

**Checks**
- [ ] `python -m pytest -q -m "not slow and not physics" --durations=10`

---

## Phase 1 — Config model updates (backward compatible)

### Target files
- `src/cpa_sim/models/config.py`
- `src/cpa_sim/stages/amp/types.py`

### Tasks
- [ ] Introduce amp backend config variants (discriminated by `kind`) while preserving existing `simple_gain` behavior.
- [ ] Add `ToyFiberAmpCfg` fields:
  - `length_m: float`
  - `beta2_s2_per_m: float = 0.0`
  - `gamma_w_inv_m: float = 0.0`
  - `gain_db: float = 0.0`
  - `loss_db_per_m: float = 0.0`
  - `n_steps: int` (small default, e.g., 8)
  - optional center wavelength override only if required by implementation.
- [ ] Validate physically invalid values with clear errors (e.g., `length_m <= 0`, `n_steps < 1`).
- [ ] Keep config migration path explicit (existing configs continue to parse).

### Acceptance
- [ ] Existing configs using `kind: simple_gain` still run unchanged.
- [ ] New `kind: toy_fiber_amp` parses and validates deterministically.

---

## Phase 2 — Amp backend plumbing + registry wiring

### Target files
- `src/cpa_sim/stages/amp/__init__.py`
- `src/cpa_sim/stages/registry.py`
- `src/cpa_sim/stages/amp/<new_backend_file>.py`

### Tasks
- [ ] Add new backend class, e.g. `ToyFiberAmpStage` under `stages/amp/`.
- [ ] Register backend in amp stage registry map.
- [ ] Keep orchestration style consistent with existing stage classes (`LaserStage`, `StageResult`, `PolicyBag`).
- [ ] Ensure per-stage metrics/artifacts are emitted using existing conventions.

### Acceptance
- [ ] Pipeline can select toy amp backend via config `kind`.
- [ ] No regressions in current stage-order integration tests.

---

## Phase 3 — Toy fiber amp implementation (deterministic split-step)

### Numerical model (toy, documented)
For each `dz = length_m / n_steps`:
1. half linear step in frequency domain (dispersion + distributed gain/loss amplitude factor),
2. nonlinear phase in time domain: `A *= exp(1j * gamma * dz_eff * P(t))`,
3. half linear step again.

Where:
- total power gain: `G = 10^(gain_db/10)`,
- distributed power gain coefficient: `g = ln(G)/L`,
- power loss coefficient from dB/m converted to nepers/m,
- amplitude factor uses 1/2 of power exponent.

### Target files
- `src/cpa_sim/stages/amp/<new_backend_file>.py`
- `src/cpa_sim/stages/amp/utils.py` (only if shared helpers are warranted)
- `src/cpa_sim/metrics.py` (only if existing metric helpers should be reused)

### Tasks
- [ ] Recompute `field_w`, `spectrum_w`, `intensity_t` consistently with repo FFT conventions.
- [ ] Keep implementation deterministic (no hidden randomness).
- [ ] Compute and emit at least:
  - gain db/linear,
  - energy in/out,
  - peak power in/out,
  - bandwidth in/out (state exact definition),
  - estimated B-integral proxy (state approximation formula).
- [ ] Add clear inline docstring disclaimer: toy model only.

### Acceptance
- [ ] Gain-only mode reproduces expected energy scaling within tolerance.
- [ ] SPM-on mode shows measurable nonlinear broadening vs SPM-off in controlled test.

---

## Phase 4 — Tests (unit + integration-fast)

### Target files
- `tests/unit/stages/test_toy_fiber_amp.py` (new)
- optionally `tests/integration/` for tiny chain coverage if needed

### Required unit tests
- [ ] **Gain-only:** `gamma=0`, `beta2=0` → output energy scales by `10^(gain_db/10)`.
- [ ] **SPM broadening:** compare `gamma>0` vs `gamma=0` with same gain and seed, assert broader output spectrum metric.
- [ ] **CPA benefit during amplification:** stretched pulse case has smaller B-integral proxy (or equivalent nonlinear distortion metric) than direct case under chosen matching criterion.

### Test policy alignment
- [ ] Mark tests with existing marker strategy (`unit`, optionally `integration`), avoid putting toy checks into `physics` unless they are true golden physics tests.
- [ ] Keep fast-gate runtime CI-friendly.

**Checks**
- [ ] `python -m pytest -q tests/unit/stages/test_toy_fiber_amp.py --durations=10`
- [ ] `python -m pytest -q -m "not slow and not physics" --durations=10`

---

## Phase 5 — Example scripts + docs (A/B narrative)

### Target files
- `src/cpa_sim/examples/toy_amp_case_a_direct.py` (new)
- `src/cpa_sim/examples/toy_amp_case_b_cpa.py` (new)
- `docs/examples/toy-fiber-amp-spm.md` (new)
- optional `src/cpa_sim/examples/` wrappers if that pattern is needed

### Tasks
- [ ] Example A: seed pulse → toy fiber amp; print metrics and optionally save plots.
- [ ] Example B: seed pulse → stretcher (`phase_only_dispersion` or equivalent) → toy fiber amp → Treacy compressor.
- [ ] Explicitly document matching criterion (energy vs compressed peak power).
- [ ] Include disclaimer block:
  - toy model,
  - no ASE,
  - no pump depletion,
  - no wavelength-dependent gain unless added.
- [ ] Keep plotting optional (`matplotlib` guarded import).

### Acceptance
- [ ] Docs provide run commands and expected qualitative outcomes.
- [ ] Scripts run without manual edits in a clean dev env (except optional plotting).

---

## Phase 6 — Final repo hygiene + release notes

### Target files
- `STATUS.md`
- `README.md` (if user-facing backend matrix is listed there)

### Tasks
- [ ] Update `STATUS.md` with what changed (backend, tests, docs, limitations).
- [ ] If relevant, add a short changelog/release-note section summarizing assumptions.
- [ ] Verify ruff line length `<=100` in touched files.

**Required checks (from repo policy)**
- [ ] `python -m pre_commit run -a`
- [ ] `python -m mypy src`
- [ ] `python -m pytest -q -m "not slow and not physics" --durations=10`

---

## Suggested implementation order for an agent

1. Config model + registry plumbing (no numerics yet).
2. Minimal gain-only toy backend (green tests for gain path).
3. Add dispersion/SPM split-step.
4. Add B-integral/bandwidth metrics.
5. Add A/B unit tests.
6. Add scripts + docs + STATUS update.
7. Run required checks and tighten tolerances only after deterministic stability is confirmed.

---

## Risks and reviewer checkpoints

### Human-supervised decisions
- [ ] Physical defaults (`beta2`, `gamma`, lengths, gain) to avoid misleading realism.
- [ ] Matching criterion narrative for A/B comparison.
- [ ] Whether B-integral estimator is sufficiently clear for docs audience.

### Agent-safe work
- [ ] Stage/config plumbing.
- [ ] Deterministic split-step implementation.
- [ ] Tests and example scripts.
- [ ] Docs formatting/lint/compliance.

---

## Definition of done

- [ ] `toy_fiber_amp` backend selectable via config and runs in pipeline.
- [ ] Required CI checks pass.
- [ ] New tests cover gain-only and SPM behavior, plus stretched-vs-direct nonlinear metric comparison.
- [ ] Example docs/scripts demonstrate A and B clearly, including matching criterion and limitations.
- [ ] `STATUS.md` and relevant ADR/documentation updated to reflect assumptions and scope.
