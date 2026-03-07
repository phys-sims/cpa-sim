# cpa-sim agent context: ML tuning inside the repo

This file is a condensed implementation contract for agents/Codex working on ML-based tuning in `cpa-sim`.

## Goal

Add easy-to-use bounded optimization and fitting workflows directly inside `cpa-sim`.

Do **not**:
- create a separate ML repo,
- modify `cpa-test-bench` for this MVP,
- move CPA-specific physics or objective logic into `phys-sims-utils`.

## Current direction

The tuning layer lives in a new subpackage:

```text
src/cpa_sim/tuning/
  __init__.py
  schema.py
  parameter_space.py
  adapter.py
  objectives.py
  cli.py
```

Add a new CLI surface under:

```text
cpa-sim tune ...
```

The first useful commands should be:
- `cpa-sim tune run --config tuning.yaml` (generic engine)
- `cpa-sim tune treacy-separation` (first vertical slice)
- `cpa-sim tune infer-n2` (second vertical slice)

`min-fiber-length` and broader end-to-end tuning can come after the generic engine is stable.

## Dependency contract

Assume `phys-sims-utils` is consumed as a normal package dependency from PyPI.

`cpa-sim` should add an optional extra:

```toml
[project.optional-dependencies]
ml = [
  "phys-sims-utils[ml]>=0.2.0",
]
```

CI and any test job that touches tuning should install:

```bash
pip install -e .[dev,ml]
```

Do **not** build any local-path or mono-repo-only install assumption into the code.

## Boundary with phys-sims-utils

Use `phys-sims-utils` only for generic optimizer plumbing.

Expected reused pieces:
- `Parameter`
- `ParameterSpace`
- `SimulationEvaluator`
- `OptimizationRunner`
- `OptimizationLogger`
- `CMAESStrategy`
- canonical `EvalResult`

Keep these in `cpa-sim`:
- spectral CSV loading and preprocessing,
- wavelength/frequency grid alignment,
- normalization and ROI logic,
- CPA-specific objectives,
- Treacy/n2/fiber-length task wrappers,
- best-run plots and CPA-specific summaries.

## Evaluation contract

Every tuning evaluation should follow this pattern:

1. Load base pipeline YAML into a plain dict.
2. Apply bounded parameter values by dot path.
3. Set `runtime.seed` deterministically.
4. Validate with `PipelineConfig.model_validate(...)`.
5. Run `run_pipeline(cfg, policy={"cpa.emit_stage_plots": False})`.
6. Compute a scalar objective plus small metric/artifact metadata.
7. Return canonical `EvalResult`.

The tuning adapter must stay thin and deterministic.

## Configuration approach

Operate on the YAML-derived dict **before** constructing `PipelineConfig`.

Do not hard-code a brittle mapping that depends on one frozen schema snapshot.
Dot-path parameter edits are the compatibility layer.

Examples of valid tunable paths:
- `stretcher.separation_um`
- `compressor.separation_um`
- `fiber.physics.length_m`
- `amp.physics.n2_m2_per_w`

Support bounds on all tunable parameters.
Support optional transforms where useful, especially log-scale for `n2`.

## Output/storage conventions

There should be exactly one tracked convention for generated run outputs:

- Use `out/` as the root for generated outputs.
- Do **not** introduce or keep a competing top-level `artifacts/` directory.
- Inside each run directory, files like `artifacts.json`, `metrics.json`, plots, traces, and best configs are fine.
- "artifact" is a file/report concept, not a top-level directory name.

Recommended layout:

```text
out/
  runs/
  tuning/
    treacy/
    n2/
    optimize/
```

Recommended tuning run contents:
- `metrics.json` or equivalent summary
- `artifacts.json`
- `history.jsonl`
- `history.csv`
- `best_config.yaml`
- `best_run/` (optional rerun with plots enabled)

## Private lab data and scratch outputs

For this MVP, keep private / non-committed lab files out of the tracked tree.

Use a gitignored local area such as:

```text
local/
  experimental/
  scratch/
```

Examples:
- raw experimental spectra CSVs
- digitized plot exports
- one-off fitting notebooks
- temporary comparisons not intended for CI

Do **not** require a tracked `data/` directory yet.

If later needed for docs/CI, add a small tracked `data/targets/` directory containing only tiny deterministic example assets generated from `cpa-sim` itself.
That is optional and **not** part of the MVP.

## Testing expectations

Keep tests deterministic and CI-friendly.

Add:
- unit tests for dot-path patching,
- unit tests for objective functions,
- integration tests for a tiny generic optimization,
- an integration/regression test for Treacy tuning,
- a synthetic recovery test for `infer-n2`.

Do not require private lab data for tests.
Do not put large numeric assets into the repo.

## Optimizer guidance

For the MVP, a single uniform path using `CMAESStrategy` is acceptable if it speeds implementation.

However:
- 1D problems (`n2`, single Treacy separation) are not ideal CMA-ES use cases.
- A bounded scalar method is a good later addition, but not required to ship the first version.

Do not over-engineer optimizer abstraction before the first end-to-end workflow works.

## Non-goals for this MVP

- No `cpa-test-bench` integration.
- No notebooks as the primary interface.
- No repo split.
- No heavy refactor of core stages or pipeline.
- No migration of CPA-specific code into `phys-sims-utils`.

## Implementation style rules

- Prefer minimal diffs.
- Preserve existing public APIs unless the change is deliberate and justified.
- Reuse `run_pipeline` and existing config/state models.
- Default tuning evaluations to plots off.
- Rerun only the best candidate with plots on when requested.
- Keep user-facing CLI and output layout simple.

## Practical priority order

1. Add `ml` extra and tuning package scaffold.
2. Implement the generic adapter + runner path.
3. Add reusable objectives / target loading.
4. Ship `treacy-separation`.
5. Ship `infer-n2`.
6. Add broader schema-driven optimization.

The point is to get to working ML tooling fast without creating repo or packaging churn you will throw away.
