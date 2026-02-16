# cpa-sim Roadmap (v1 → v3)

_Last updated: 2026-02-15_
_Owner: Ryaan Lari_

This roadmap is organized as **release versions** (v1, v2, v3).
Code should be organized by **stage type + backend** (e.g., `stages/fiber/gnlse.py`, `stages/fiber/gnlse_sim.py`), not by version folders.

---

## North-star outcomes

- **v1 (Credible baseline):** A reproducible CPA chain that runs end-to-end with reputable external solvers/models, produces key metrics and plots, and has a clean API + CI discipline.
- **v2 (Ecosystem integration):** Swap v1 backends with phys-sims org repos (`gnlse-sim`, `abcdef-sim`) while preserving the public API and validation tiers.
- **v3 (Lab-facing product):** Scalable sweeps + ML/testharness integration via `phys-sims-utils`, leveraging `phys-pipeline` caching/scheduling, with high-quality reports and regression protection.

---

## Repo boundaries

### `cpa-sim` (library/product)
- Stages, configs, metrics, provenance, CLI, minimal examples, fast CI.
- A small number of pinned “golden” physics tests.

### `cpa-testbench` (showcase + heavy validation)
- Slow sweeps, experimental comparisons, large plots, notebooks.
- Anything that shouldn’t run in library CI.

---

## Global conventions (must be decided early)

These are **human-owned** decisions. Write them into ADRs and keep them stable.

- Units: time (s/fs/ps), frequency (Hz vs rad/s), wavelength units, fiber params.
- Fourier transform convention and normalization.
- Dispersion sign conventions (β₂ sign, chirp sign).
- Power/energy definitions and how envelope amplitude maps to physical units.
- Tolerances and how you define “match” for solver examples.

**Deliverable:** `docs/adr/ADR-0001-conventions.md` + a short “Conventions” section in README.

---

## Validation strategy (used in all versions)

### Validation tiers
- **Unit tests (fast):** shape, dtype, serialization, config validation, invariants (energy conserved for phase-only).
- **Theoretical physics tests (pinned):** reproduce a canonical example (from solver docs or known analytic case).
- **Experimental physics tests (bench):** compare to paper/lab data; report error bars and known confounds.

### Reporting format (schema)
- Every comparison yields a machine-readable record:
  - tier: THEORETICAL | EXPERIMENTAL
  - reference: citation string + link
  - metrics compared + tolerances
  - result: pass/fail + numeric errors
  - provenance: versions, git SHA, environment

**Deliverable:** `cpa_sim/reporting/validation_models.py` + `cpa_sim/reporting/report.py`

---

# v1 — Credible baseline (external solvers + fixed free-space model)

## v1 Definition of Done
1. CLI: `cpa-sim run config.yaml --out out/` works on a clean machine.
2. End-to-end chain runs: **stretcher → fiber → amp → compressor**.
3. Outputs:
   - `metrics.json` (per stage + overall)
   - plots for temporal intensity + spectrum per stage
   - optional `.npz` states for reproducibility
4. CI:
   - fast tests run on every PR
   - physics tests are separate (nightly/manual) if slow
5. At least **one** pinned theoretical physics test for fiber stage and **one** for free-space stage.

---

## v1 Workstreams and tasks

### A) Repo scaffolding and engineering hygiene (agent-safe)
- [ ] Create repo via cookiecutter (src layout).
- [ ] `pyproject.toml` with pinned runtime deps and optional extras (`dev`, `plots`).
- [ ] Tooling: ruff + mypy + pytest + pre-commit.
- [ ] GitHub Actions:
  - [ ] `ci.yml` (lint, typecheck, unit+integration tests)
  - [ ] `physics.yml` (nightly/manual, runs physics tests)
- [ ] Project docs skeleton:
  - [ ] `README.md` with a runnable quickstart
  - [ ] `AGENTS.md` rules for agents (CI green, markers, update STATUS.md)
  - [ ] `STATUS.md` “source of truth” health report
  - [ ] `docs/adr/INDEX.md` + reindex script (optional)

**Agent-safe:** yes.

---

### B) Public API + data model (mostly agent-safe; human owns conventions)
- [ ] Define **PulseGrid**, **PulseState**, **StageResult**, **Provenance** models.
- [ ] Define per-stage config models with discriminators:
  - FiberCfg(kind="gnlse" | ...)
  - FreeSpaceCfg(kind="tracy_grating" | ...)
  - AmpCfg(kind="simple_gain" | ...)
- [ ] Stable hashing for configs (cache keys) and provenance capture.
- [ ] Stage registry: config.kind → backend implementation.

**Human:** decide conventions; review data model decisions.
**Agent-safe:** implementation + tests.

---

### C) FreeSpaceStage v1 — fixed Tracy grating equation (human must provide truth target)
- [ ] Implement `stages/free_space/tracy_grating.py`
  - phase-only spectral transform (or whichever domain the equation dictates)
  - supports stretcher/compressor via parameters
- [ ] Unit tests:
  - [ ] energy conserved for phase-only operation
  - [ ] grid consistency and parameter validation
- [ ] Theoretical physics “golden” test:
  - [ ] pick one reference case with expected output summary metrics
- [ ] ADR:
  - [ ] what’s included/excluded (no aberrations, no spatial effects, etc.)

**Human:** supply equation + one numeric reference case + sign conventions.
**Agent-safe:** implementation, tests, ADR draft.

---

### D) FiberStage v1 — wrap external GLNSE solver (agent-safe with human review)
- [ ] Choose solver (recommended: `gnlse` from WUST-FOG) and pin version.
- [ ] Distinguish this from the v2 in-house `gnlse-sim` backend (formerly `fiber-sim`) in docs/config notes.
- [ ] Implement wrapper `stages/fiber/gnlse.py`
  - map FiberCfg → solver parameters
  - normalize I/O to PulseState + PulseGrid conventions
- [ ] Unit tests:
  - [ ] wrapper input validation and error messages
  - [ ] output shapes/dtypes, reproducibility seeds (if applicable)
- [ ] Theoretical physics test:
  - [ ] reproduce one canonical example from solver docs and pin metrics
- [ ] Docs:
  - [ ] `docs/agent/gnlse_context.md` (condensed solver API notes)
- [ ] ADR:
  - [ ] solver choice rationale + replacement conditions

**Human:** choose solver + tolerances; review mapping.
**Agent-safe:** wrapper, tests scaffolding, doc condensation.

---

### E) AmpStage v1 — simple gain model (agent-safe)
- [ ] Implement `stages/amp/simple_gain.py`
  - linear gain in dB, optional saturation stub (not active in v1)
  - consistent amplitude/energy scaling
- [ ] Unit tests:
  - [ ] scaling checks, config validation
- [ ] ADR proposal:
  - [ ] future EDFA model / noise figure / gain dynamics

**Agent-safe:** yes.

---

### F) End-to-end runner + CLI (agent-safe)
- [ ] Implement `cpa_sim/pipeline.py` composing stages.
- [ ] CLI (Typer):
  - [ ] `cpa-sim run <config.yaml> --out <dir>`
  - [ ] `cpa-sim validate <config.yaml>` (optional)
- [ ] Output artifacts:
  - [ ] `metrics.json`
  - [ ] plots (PNG) per stage
  - [ ] states saved as `.npz` (toggle)

**Agent-safe:** yes.

---

### G) Reporting + validation schema (agent-safe; human interpretation)
- [ ] ValidationCase schema with tiers.
- [ ] Report generator:
  - [ ] JSON + Markdown summary
  - [ ] includes provenance (git SHA, versions, OS, python)
- [ ] Add 1–2 example validations integrated into CLI output.

**Human:** approve what’s claimed; agent can implement mechanics.

---

### H) v1 release and demo (agent-safe with human final review)
- [ ] Add `CHANGELOG.md`, versioning, package metadata.
- [ ] Add minimal tutorial config + expected outputs.
- [ ] Publish v1 to PyPI (or tag release if internal).
- [ ] Create `cpa-testbench` skeleton and a “lab demo” notebook/script:
  - [ ] “Before/after” plots that sell the concept.

**Human:** final QA and any public claims.

---

## v1 risks and mitigations
- **Ambiguous sign conventions** → lock ADR early + pinned golden tests.
- **Solver mismatch** (units/scaling) → validate with solver canonical example first.
- **CI gets slow** → marker discipline + nightly physics tests.

---

# v2 — Ecosystem integration (gnlse-sim + abcdef-sim backends)

## v2 Definition of Done
1. `cpa-sim` public API stays stable (configs may add a new `kind`, but old ones still work).
2. Fiber backend selectable: `kind="gnlse_sim"` (new name; formerly `fiber_sim`).
3. Free-space backend selectable: `kind="abcdef_grating"` (or equivalent).
4. Validation/reporting schema expanded to record:
   - theoretical-vs-experimental error as separate objects
   - “model error” vs “measurement/fit error” fields (where applicable)
5. At least one pinned theoretical test for each new backend.

---

## v2 Workstreams and tasks

### A) Build `gnlse-sim` (new repo; previously `fiber-sim`) to replace external solver (human + agent)
**Goal:** ML-friendly, stable configs, deterministic runs, explicit parameterization.

Core tasks:
- [ ] Repository skeleton + CI (agent-safe).
- [ ] GLNSE engine:
  - [ ] SSFM integrator with pluggable step control
  - [ ] optional Raman/self-steepening hooks
- [ ] Config and state model compatible with `phys-pipeline` style stages.
- [ ] Determinism:
  - [ ] stable seeds, reproducible grids, consistent FFT choices
- [ ] Validation:
  - [ ] match one `gnlse` canonical example within tolerance (theoretical tier)
- [ ] Export interface used by cpa-sim wrapper:
  - [ ] `simulate_fiber(state, cfg) -> state_out`

**Human:** algorithm choices, numerical stability decisions.
**Agent-safe:** repo scaffolding + lots of implementation once spec is clear.

---

### B) Integrate `gnlse-sim` into cpa-sim (agent-safe)
- [ ] Add `stages/fiber/gnlse_sim.py` backend implementing the same interface (or keep `fiber_sim.py` as compatibility alias if needed).
- [ ] Expand FiberCfg union: add kind="gnlse_sim" (and optionally retain `fiber_sim` as deprecated alias).
- [ ] Add theoretical regression tests.

---

### C) Build/finish `abcdef-sim` for grating comps/stretchers (human + agent)
**Goal:** physically motivated free-space model (dispersion + ray/beam handling).

Core tasks:
- [ ] Implement grating stretcher/compressor modules with dispersion support.
- [ ] Provide a “reduced mode” that matches v1 Tracy model under simplifying assumptions.
- [ ] Validation:
  - [ ] theoretical match against v1 Tracy for the overlapping regime
  - [ ] additional checks vs known ray/ABCD references where applicable

**Human:** optics modeling decisions and scope.
**Agent-safe:** engineering implementation + tests scaffolding.

---

### D) Integrate `abcdef-sim` into cpa-sim (agent-safe)
- [ ] Add `stages/free_space/abcdef_grating.py` backend.
- [ ] Expand FreeSpaceCfg union: add kind="abcdef_grating".
- [ ] Keep v1 backend available and tested.

---

### E) Upgrade validation reporting (human defines what “error” means)
- [ ] Extend schema:
  - model_error (theoretical deviation)
  - experimental_error (measurement/fit uncertainty)
- [ ] Standardize plots:
  - error vs parameter sweeps
  - error budget breakdown
- [ ] Move most experimental comparisons to `cpa-testbench`.

---

### F) v2 release deliverables
- [ ] `cpa-sim` supports both external solver and in-house backends.
- [ ] `gnlse-sim` (formerly `fiber-sim`) and `abcdef-sim` released (or at least tagged).
- [ ] Migration notes in docs.

---

# v3 — Lab-facing product (ML/testharness + scalable sweeps)

## v3 Definition of Done
1. Large parameter sweeps run efficiently using `phys-pipeline` stage caching and scheduling.
2. `research-utils` testharness + ML tools integrated:
   - batch evaluation interface
   - standardized experiment runner
   - report generation (tables + plots + provenance)
3. Clear regression protection:
   - baseline runs pinned
   - change impact reports produced automatically
4. Usable by lab members:
   - “one command” to run a sweep and generate a report
   - documented configs and examples

---

## v3 Workstreams and tasks

### A) Phys-pipeline wrapper hardening (agent-safe with human review)
- [ ] Make `cpa-sim` a first-class phys-pipeline wrapper:
  - each stage implements Stage API
  - stage-level cache keys stable and explicit
- [ ] Add scheduler hooks for sweeps:
  - stage-aware recomputation
  - batch execution with caching wins
- [ ] Provide a clean “pipeline config” that composes stages by reference.

---

### B) research-utils integration (mixed)
- [ ] Define experiment templates:
  - sweep over dispersion, fiber length, gain, compressor spacing, etc.
- [ ] Add ML optimization hooks:
  - Bayesian optimization / evolutionary search / gradient-free
  - pluggable objective functions
- [ ] Standard reporting:
  - per-run metrics + aggregated Pareto fronts
  - provenance and reproducibility
- [ ] Automatic “change report”:
  - compare main branch vs PR branch on a small benchmark suite

**Human:** decide which optimization methods to support and what is “success.”
**Agent-safe:** tooling glue + report generation once spec is set.

---

### C) Testbench becomes the public narrative (agent-safe)
- [ ] `cpa-testbench` hosts:
  - canonical demos (wow plots)
  - lab calibration comparisons
  - publication-ready figures
- [ ] Add `make report` style entrypoints (or `python -m ...`).

---

### D) Release engineering and stability (agent-safe)
- [ ] Nightly benchmark runs stored as artifacts.
- [ ] Semantic versioning and deprecation policy (esp. for backends).
- [ ] Documentation upgrades:
  - “How to add a new stage backend”
  - “How to add a new validation case”
  - “How to run sweeps on ICC/HPC”

---

## Suggested ADR list (minimum set)
- ADR-0001: conventions (units, transforms, sign)
- ADR-0002: stage interface + state model
- ADR-0003: fiber solver choice (v1) + replacement triggers
- ADR-0004: free-space model scope (v1) + limits
- ADR-0005: validation tiers + tolerances + reporting
- ADR-0006: caching keys and provenance requirements

---

## Minimal example config (v1)

```yaml
grid:
  n: 2**13
  t_window: 200e-12
  center_wavelength: 1560e-9

pulse:
  kind: sech2
  fwhm: 1.0e-12
  energy: 1.0e-9
  chirp: 0.0

stretcher:
  kind: tracy_grating
  params:
    # fill with your equation parameters
    ...

fiber:
  kind: gnlse
  params:
    length: 10.0
    beta2: -20e-27
    gamma: 1.3e-3
    ...

amp:
  kind: simple_gain
  params:
    gain_db: 20.0

compressor:
  kind: tracy_grating
  params:
    ...
```

---

## Agent vs Human ownership summary

### Safe for an agent (Codex)
- Scaffolding, CI, formatting, markers
- Stage registry + config unions
- CLI plumbing + config parsing
- Wrappers around external libs (with human review)
- Report generation + artifact saving
- Most unit tests + slow-test separation

### Human must do
- Conventions (units/sign/FT)
- Provide golden numeric reference cases for free-space + fiber examples
- Decide tolerances and what “match” means
- Approve any “experimental validation” claims and references
- Decide scope boundaries between repos

---

_End._
