# AGENTS

## Scope
This file applies to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory.

This repository is **cpa-sim**, a modular **chirped-pulse amplification (CPA)** simulator. It provides a stable, testable pipeline for
**stretcher → fiber propagation → amplification → compressor**, with consistent conventions, provenance, and validation tiers.

**v1 policy:** Prefer reputable external solvers/models (e.g., GLNSE library + fixed grating equation) instead of reimplementing physics.  
**v2/v3:** Add in-house backends (`fiber-sim`, `abcdef-sim`) and ML/testharness integration while keeping the public API stable.

---

## Operating principles

### 1) Backends behind small interfaces
Keep each stage behind a small internal interface so implementations can be swapped without changing the public config shape.

- Stage types live under `cpa_sim/stages/<stage_type>/`
- Each stage type can have multiple **backends** (files), selected by `cfg.kind`
  - Example: `FiberCfg(kind="gnlse")` → `stages/fiber/gnlse.py`
  - Example: `FreeSpaceCfg(kind="tracy_grating")` → `stages/free_space/tracy_grating.py`

Avoid “version folders” (`v1/`, `v2/`) inside the code. Versions are **releases**, not a code organization strategy.

### 2) Strict conventions + explicit assumptions
Units, FFT conventions, and dispersion/chirp sign conventions must be explicit and stable. Any change requires:
- an ADR
- updated physics tests (golden targets)
- a `STATUS.md` update

### 3) Deterministic reproducibility
Same config + same seed must produce the same key outputs (within defined float tolerances). No hidden randomness.

### 4) Validation tiers (don’t overclaim)
- **Unit tests (fast):** shape/typing/serialization/invariants.
- **Theoretical physics tests:** reproduce canonical solver examples or analytic checks.
- **Experimental comparisons:** belong primarily in `cpa-testbench` and must be framed with uncertainty/error bars.

### 5) Provenance is part of the product
Every run should be able to produce:
- version info, git SHA
- environment info (python, OS)
- config hash
- stage-level artifacts/metrics paths

---

## Key references (must read first)
- `docs/adr/ADR-0001-conventions.md` — units/FFT/sign conventions (create early).
- `docs/adr/ADR-0002-stage-interface.md` — StageResult, State, artifact policy.
- `docs/adr/ADR-0003-validation-tiers.md` — what is tested and how.
- `docs/agent/context.md` — condensed agent context for backends and mapping rules.
- `cpa_sim/models/` — PulseGrid, PulseState, StageResult, Provenance models.
- `configs/examples/` — canonical example configs (kept CI-friendly).

If these files don’t exist yet, create minimal stubs and iterate.

---

## End-goal acceptance criteria (per release)

### v1 (baseline)
1) CLI: `cpa-sim run config.yaml --out out/` works on a clean machine.
2) End-to-end chain runs: **stretcher → fiber → amp → compressor**.
3) Outputs:
   - `metrics.json` per stage + overall
   - plots (time intensity + spectrum) per stage
   - optional intermediate `.npz` states
4) CI discipline:
   - fast tests on PRs
   - physics tests separate (nightly/manual) if slow
5) At least one pinned theoretical test for:
   - `FreeSpaceStage` backend
   - `FiberStage` backend

### v2 (ecosystem backends)
- Add `kind="fiber_sim"` (fiber-sim backend) and `kind="abcdef_grating"` (abcdef-sim backend) without breaking v1 configs.
- Add theoretical regression tests for each new backend.

### v3 (lab-facing)
- Integrate `phys-pipeline` caching/scheduling + `research-utils` ML/testharness.
- Add reproducible sweep runner + standardized reports.

---

## Repository boundaries and responsibilities

This repo owns:
- CPA pipeline stages and stable internal models
- conventions + ADRs
- determinism, provenance, artifact generation
- tests and validation scaffolding
- CLI and minimal examples

Recommended separate repos:
- `cpa-testbench`: slow sweeps, paper/lab comparisons, notebooks, “wow plots”
- `fiber-sim`: your in-house GLNSE engine (v2)
- `abcdef-sim`: your in-house free-space grating/back-prop model (v2)
- `research-utils`: ML + testharness + report tooling
- `phys-pipeline`: staging/caching/scheduling substrate

Do not move CPA physics logic into UI/MCP repos.

---

## Architecture: stage chain (v1)
Recommended stage chain (names may differ, but responsibilities should match):

- `PulseInitStage` — create initial pulse from config (sech²/gaussian/etc)
- `FreeSpaceStage` — stretcher (phase/dispersion model)
- `FiberStage` — nonlinear propagation (external GLNSE in v1)
- `AmpStage` — gain model (simple in v1)
- `FreeSpaceStage` — compressor (same backend as stretcher, different params)
- `MetricsStage` — compute summary metrics and generate plots
- `ReportStage` (optional) — validation report + provenance summary

### External solver integration rule
Isolate external solver calls behind `cpa_sim/stages/<type>/<backend>.py` and (if needed) `cpa_sim/backends/<solver>/`.
Avoid scattering raw third-party API calls across the codebase.

---

## State model (stable shape)
Use one stable `PulseState` throughout all stages. Populate it progressively.

Recommended fields:
- `meta`: run id, seed, config hash, version, timestamps
- `grid`: PulseGrid (t, w, dt, dw, center_wavelength)
- `field`: complex envelope arrays (prefer references if large)
- `derived`: spectrum, intensity (cached or computed-on-demand)
- `metrics`: small scalars (energy, FWHM, bandwidth, B-integral estimate)
- `artifacts`: paths/refs to plots and arrays saved to disk

### Large arrays policy
Prefer passing references (paths/npz keys) rather than embedding huge arrays in JSON-like outputs.
Keep run outputs reproducible and bounded in size.

---

## Determinism / RNG rules
- All randomness derived from a single seed in config (e.g., `runtime.seed`).
- Derive per-stage RNG streams deterministically (or pass a RNG through State).
- Determinism tests must lock key summary outputs (tolerant floats, exact discrete).

---

## Tests (required)

### Unit tests (fast)
- Config validation errors are clear and structured.
- Energy conservation where only phase is applied.
- Serialization/hashing stability for configs and small states.

### Integration tests (fast-ish)
- End-to-end run on a tiny grid config in <10s (CI-friendly).
- Asserts output files exist, key metrics finite.

### Physics tests (may be slower)
- Free-space: one pinned “golden” case (your trusted numeric target).
- Fiber: reproduce one canonical solver example and pin summary metrics.

**Pytest markers**
- `unit`, `integration`, `physics`, `slow`  
CI on PRs should run only fast tests; physics/slow should run nightly or manual.

---

## Documentation via ADRs (required)
Use ADRs for:
- conventions and sign rules
- stage interfaces and caching/provenance policies
- backend choices (gnlse vs alternatives)
- validation tiers and tolerances
- artifact formats (npz schema, plot naming)

Each ADR must state how the decision is validated (unit/integration/physics tests).

---

## Developer workflow (CI must stay green)

### Required checks (must pass)
- Pre-commit:
  - `python -m pre_commit run -a`
- Type checking:
  - `python -m mypy src`
- Tests (fast gate):
  - `python -m pytest -q -m "not slow and not physics" --durations=10`

### Optional checks
- Physics tests:
  - `python -m pytest -q -m physics --durations=10`
- Slow tests:
  - `python -m pytest -q -m slow --durations=10`
- Full suite:
  - `python -m pytest -q -m "slow or physics or (not slow and not physics)" --durations=10`

### Rules
- Do not submit a PR that fails any required checks.
- Keep docs/examples synchronized with behavior.
- Update `STATUS.md` whenever behavior, tests, or schemas change.
- When updating timestamps, use the system `date` command (or `date -u`); do not guess.

---

## Guardrails
- Prefer correctness + clarity over micro-optimizations.
- Prefer reputable third-party solvers/models in v1 over bespoke rewrites.
- Never silently ignore invalid config combinations; validate and raise structured errors.
- Don’t change public config/result shape without ADR + tests + versioning policy.
