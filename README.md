# cpa-sim

_A modular chirped-pulse amplification (CPA) simulation package._

`cpa-sim` is a physics-oriented pipeline for modeling a canonical CPA chain:
**pulse initialization → stretcher → fiber propagation → amplification → compressor → metrics**.

The project is structured to keep stage interfaces stable while allowing backend implementations to evolve (for example, from placeholder deterministic transforms to solver-backed physics models).

## Why this project exists

CPA experiments and design studies need repeatable simulation workflows with:

- consistent units and sign conventions,
- deterministic runs (same config + seed → same summary outputs),
- stage-level provenance and metric reporting,
- test tiers that separate fast contract checks from slower physics regression checks.

`cpa-sim` focuses on those software guarantees first so model fidelity can scale safely over time.

## Stage flow

The default v1 chain is shown below.

```mermaid
flowchart LR
    A[PulseInitStage\nInitialize pulse and grid] --> B[FreeSpaceStage\nStretcher]
    B --> C[FiberStage\nNonlinear propagation]
    C --> D[AmpStage\nGain model]
    D --> E[FreeSpaceStage\nCompressor]
    E --> F[MetricsStage\nCompute metrics and plots]
    F --> G[ReportStage (optional)\nSummarize provenance and validation]
```

## Current implementation snapshot

The repository currently provides:

- a deterministic sequential pipeline builder and runner,
- typed configuration/state models,
- stage registries/backends for laser generation, free-space, fiber, amplification, and metrics,
- test markers for `unit`, `integration`, `physics`, and `slow` workflows.

See `STATUS.md` for progress tracking and release-readiness checklists.

## Installation

### Runtime install

```bash
pip install -e .
```

### Development install

```bash
pip install -e .[dev]
# optional WUST-FOG backend dependency
pip install -e .[gnlse]
```

## Quickstart (Python API)

> CLI ergonomics are on the roadmap; current usage is Python-first.

```python
from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline

cfg = PipelineConfig()  # start from deterministic defaults
result = run_pipeline(cfg)

print(result.metrics)
print(result.state.meta)
```

## Configuration model (high-level)

The top-level `PipelineConfig` includes these sections:

- `runtime` (seed and run controls),
- `laser_gen` (initial pulse/beam specification),
- `stretcher` / `compressor` defaults (free-space configs used when `stages` is not set),
- `fiber` (`FiberStageCfg` with stable `physics` plus backend-specific `numerics`),
- `amp` (amplifier backend + gain; supports `simple_gain` and `toy_fiber_amp`),
- `stages` (optional arbitrary ordered list of `free_space`, `fiber`, and `amp` stage configs),
- `metrics` (summary metric backend; always appended at pipeline end).

This keeps public configuration stable while backend selection happens per stage via `kind`.

### Runtime config vs stage config vs pipeline policy

- `runtime` is **run-level metadata/control** (for example seed) and is not a processing stage.
- stage configs (`laser_gen`, `stretcher`, `fiber`, `amp`, `compressor`, `metrics`) define model parameters and backend `kind` per stage.
- `policy` is a pipeline-wide override bag passed at execution time for cross-cutting controls (debug/tolerances/instrumentation) without changing stage config shape.

In short: `runtime` and `policy` are global execution concerns, while stage configs define the physical chain itself.

### Configurable stage ordering

`PipelineConfig.stages` allows arbitrary permutations of free-space, fiber, and amp stages.
When omitted, the legacy default order remains `stretcher -> fiber -> amp -> compressor`.
`laser_gen` is always the first stage and `metrics` is always the final stage, so baseline
runs without stretching/compression can be expressed by omitting free-space entries from `stages`.

### Stage plot policy

Pass runtime policy `{"cpa.emit_stage_plots": true}` to emit per-stage time/spectrum SVG plots.
Use `"cpa.stage_plot_dir"` to control the output directory (default: `artifacts/stage-plots`).


## Fiber stage example (WUST `gnlse`)

A runnable fiber-stage example script is available at:

- `scripts/examples/wust_gnlse_fiber_example.py`

Run it with:

```bash
python scripts/examples/wust_gnlse_fiber_example.py --out artifacts/fiber-example --format svg
```

For configuration/units details, see `docs/examples/wust-gnlse-fiber-example.md`.

Canonical end-to-end 1560 nm chain example documentation is at:

- `docs/examples/canonical-1560nm-chain.md`


Toy amplifier A/B example documentation is available at:

- `docs/examples/toy-fiber-amp-spm.md`


## Outputs and provenance

A run returns a `StageResult` with:

- `state`: pulse/beam state plus `meta`, `metrics`, and `artifacts`,
- `metrics`: stage and aggregate metric namespace entries,
- `meta`: provenance data including deterministic run metadata.

At minimum, the package aims to keep summary metrics finite and reproducible for fixed config/seed pairs.

## Validation strategy

The test strategy follows tiered validation:

- **Unit tests** for schema contracts and invariants,
- **Integration tests** for end-to-end tiny-chain execution,
- **Physics tests** for canonical/golden targets (tracked as roadmap work),
- **Slow tests** for larger or longer-running scenarios.

Common local commands:

```bash
python -m pre_commit run -a
python -m mypy src
python -m pytest -q -m "not slow and not physics" --durations=10
```

## Repository layout

```text
src/cpa_sim/
  models/            # configuration, state, provenance models
  stages/            # stage interfaces + backend implementations
  pipeline.py        # chain assembly and deterministic execution entrypoint

tests/
  unit/              # fast contract/invariant tests
  integration/       # fast end-to-end smoke tests
  physics/           # canonical physics regression tests
```

## Roadmap themes

Near-term focus areas include:

1. maturing physics backends and canonical reference cases,
2. expanding artifact/report generation,
3. hardening schema/contract documentation,
4. introducing a stable CLI workflow.

For concrete status, see `STATUS.md` and ADRs in `docs/adr/`.

## Contributing

Before opening a PR, run required quality gates:

```bash
python -m pre_commit run -a
python -m mypy src
python -m pytest -q -m "not slow and not physics" --durations=10
```

Keep docs and status files synchronized when behavior changes.

## License

See `LICENSE`.
