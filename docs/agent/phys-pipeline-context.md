# phys-pipeline context for bootstrapping `cpa-sim`

This document distills the `phys-pipeline` docs into an implementation-oriented context that an agent can use to build the foundation of `cpa-sim` quickly and safely.

---

## 1) What to copy from `phys-pipeline` (mental model)

`phys-pipeline` is a **typed execution substrate** for simulation stages. The useful baseline for `cpa-sim` is:

- a stable `State` object flowing through stages,
- immutable typed stage configs,
- deterministic, pure-ish stage transforms,
- scalar metrics + optional heavy artifacts,
- reproducibility via provenance + hashing,
- a sequential pipeline first, DAG capability second.

For `cpa-sim`, this means building the CPA chain as composable stages (`pulse init -> free-space stretcher -> fiber -> amp -> free-space compressor -> metrics/report`) while preserving deterministic contracts.

---

## 2) Core contracts to adopt first

### 2.1 `State` contract (single stable shape)

Mirror `phys-pipeline`'s `State` philosophy:

- stage input/output should be one stable `PulseState` model,
- `deepcopy()` semantics must be explicit,
- hashing representation should be deterministic and stable across runs.

Recommended `PulseState` top-level fields:

- `meta`: run_id, seed, config hash, version/timestamps,
- `grid`: time/frequency axes + spacing + center wavelength,
- `field`: complex envelope arrays,
- `derived`: intensity/spectrum (computed or cached),
- `metrics`: scalar summaries,
- `artifacts`: references to saved artifacts (paths/keys, not giant inline blobs).

### 2.2 `StageConfig` contract (frozen typed config)

Adopt frozen/immutable config models for every stage. This keeps runs reproducible and hash-friendly.

Minimum fields each stage config should include:

- `name` (stable stage id),
- `kind` (backend selector, e.g. `tracy_grating`, `gnlse`),
- backend-specific parameters,
- optional schema/version hints where needed.

### 2.3 `StageResult` contract

Keep return values aligned with `phys-pipeline` behavior:

- required: `state`,
- optional: `metrics` (must be scalar JSON-friendly values),
- optional: `artifacts` (lazy callables or artifact descriptors),
- optional: `provenance` additions.

Rule: heavy numerical arrays should be persisted through artifact recording and referenced from state/metrics, not serialized wholesale in metrics JSON.

---

## 3) Execution model for `cpa-sim`

### Phase A (must-have): sequential pipeline

Start with a sequential executor that:

1. validates stage list and stage configs,
2. executes stages in order,
3. merges metrics with namespaced keys,
4. records provenance per stage,
5. optionally records artifacts.

This should be the default production path for v1.

### Phase B (later): DAG/scheduler/caching upgrades

`phys-pipeline` supports DAG nodes, schedulers, and DAG-aware cache keys. Treat these as additive after sequential contracts are stable.

When adding DAG support in `cpa-sim`, preserve:

- same stage interfaces,
- same state/result schema,
- deterministic dependency semantics.

---

## 4) Provenance, policy, and hashing (must be designed early)

### 4.1 Provenance baseline

Every run should capture enough metadata to reproduce or compare:

- pipeline/stage versions,
- config fingerprint,
- policy fingerprint,
- seed,
- runtime timestamps,
- optional dependency/backend version stamps.

### 4.2 Policy bag pattern

Adopt a run-wide override container (equivalent to `PolicyBag`) for tolerances, debug toggles, resolution overrides, and instrumentation. Policy values must influence provenance/hash where they can affect outputs.

### 4.3 Cache key composition

Follow `phys-pipeline` cache-key intent:

`cache_key <- hash(state_input, stage_config, policy, stage_version)`

Do not include non-deterministic values in cache keys unless intentionally versioned.

---

## 5) Artifact strategy

Use opt-in artifact recording like `phys-pipeline`:

- default runs should return lightweight results,
- when enabled, save plots/arrays under a run artifact root,
- return stable references (paths + semantic keys),
- keep naming deterministic (`<stage>/<artifact_key>.<ext>` style).

This keeps CI fast and enables reproducible report generation.

---

## 6) Error taxonomy and validation tiers

Adopt explicit error classes and test mapping early.

Suggested categories:

- config/schema validation errors,
- stage precondition errors,
- backend integration/runtime errors,
- numerical validity errors (NaN/Inf, energy sanity),
- artifact/IO failures.

Map each category to test tiers:

- **unit**: schema + deterministic transforms,
- **integration**: end-to-end tiny CPA chain,
- **physics**: pinned canonical numerical targets,
- **slow**: large grids/sweeps.

Keep markers aligned with repository policy: `unit`, `integration`, `physics`, `slow`.

---

## 7) Concrete bootstrap blueprint for `cpa-sim`

### 7.1 Minimal package structure

```text
src/cpa_sim/
  models/
    pulse_grid.py
    pulse_state.py
    stage_result.py
    provenance.py
  policy.py
  errors.py
  pipeline.py
  stages/
    pulse_init/
      base.py
      analytic.py
    free_space/
      base.py
      tracy_grating.py
    fiber/
      base.py
      gnlse.py
    amp/
      base.py
      simple_gain.py
    metrics/
      base.py
      standard.py
```

### 7.2 Stage backend rule

Each stage type dispatches by `cfg.kind`. Keep third-party solver calls isolated in backend modules so APIs can be swapped without changing public config shapes.

### 7.3 First runnable target

Implement one tiny deterministic config that runs:

`PulseInit -> FreeSpace(stretcher) -> Fiber(gnlse adapter stub/mock if needed) -> Amp -> FreeSpace(compressor) -> Metrics`

and emits:

- `metrics.json`,
- at least one plot artifact,
- optional intermediate state dumps.

---

## 8) ADR alignment checklist (from phys-pipeline lessons)

Before major growth, ensure these decisions are documented in `cpa-sim` ADRs:

1. conventions (units/FFT/sign),
2. stage/state/result contract,
3. validation tiers + tolerances,
4. error taxonomy,
5. provenance + metric namespacing,
6. cache approach (when introduced),
7. backend selection criteria and replacement policy.

Use ADRs to tie each decision to concrete tests.

---

## 9) Implementation sequencing an agent can execute

1. Define typed models (`PulseGrid`, `PulseState`, `StageResult`, provenance models).
2. Implement deterministic sequential pipeline runner.
3. Add policy container and stable hashing helpers.
4. Add free-space + amp + metrics minimal backends; wire backend dispatch by `kind`.
5. Add one end-to-end integration test (tiny grid, CI-fast).
6. Add one pinned free-space physics test.
7. Add artifact recorder plumbing.
8. Add fiber backend adapter boundary (initially thin wrapper or stub, then real external integration).
9. Add docs/example configs matching the tests.

---

## 10) Definition of "sufficient basis" for `cpa-sim`

An agent has laid the basis when all are true:

- stage/state/result interfaces are typed and stable,
- sequential CPA chain runs deterministically from a config,
- outputs include scalar metrics + optional artifacts,
- provenance contains reproducibility-critical hashes/metadata,
- fast tests pass for contract and integration,
- at least one pinned physics reference test exists.

This mirrors the successful `phys-pipeline` foundation while leaving room for v2/v3 backend and orchestration expansion.
