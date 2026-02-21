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
    A["PulseInitStage<br/>Initialize pulse and grid"] --> B["FreeSpaceStage<br/>Stretcher"]
    B --> C["FiberStage<br/>Nonlinear propagation"]
    C --> D["AmpStage<br/>Gain model"]
    D --> E["FreeSpaceStage<br/>Compressor"]
    E --> F["MetricsStage<br/>Compute metrics and plots"]
    F --> G["ReportStage (optional)<br/>Summarize provenance and validation"]
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

## Quickstart (CLI + example configs)

Run the checked-in example configs directly with the CLI:

```bash
cpa-sim run configs/examples/basic_cpa.yaml --out out/basic
cpa-sim run configs/examples/tracy_golden.yaml --out out/tracy-golden
# optional: requires the WUST-FOG gnlse dependency
cpa-sim run configs/examples/gnlse_canonical.yaml --out out/gnlse-canonical
```

## Quickstart (Python API)

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
- `amp` (amplifier backend config; supports `simple_gain` and `toy_fiber_amp` with `amp_power_w` control),
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

CLI runs now emit per-stage time/spectrum SVG plots by default into `<out>/stage_plots/`.
If you use the Python API directly, pass runtime policy `{"cpa.emit_stage_plots": true}` and
optionally set `"cpa.stage_plot_dir"`.

### Pulse amplitude and units

`laser_gen.spec.pulse.amplitude` is treated as a **field amplitude** in `sqrt(W)` units.
That means `|E(t)|^2` is instantaneous power in watts, and pulse energy is
`sum(|E|^2 * dt_fs * 1e-15)` joules.

Practical mapping:

- choose pulse shape + width (`width_fs`) + window/grid (`time_window_fs`, `n_samples`),
- set `amplitude = sqrt(target_peak_power_w)` for the desired initial peak power,
- set `rep_rate_mhz` to your laser repetition rate; average power is then
  `pulse_energy_j * rep_rate_hz`.

For `toy_fiber_amp`, `amp_power_w` is the target **output average power in watts** at the stage output plane.


## Fiber stage example (WUST `gnlse`)

Example policy: runnable example logic lives in `src/cpa_sim/examples/*` and is invoked via module entrypoints.

A runnable fiber-stage example module is available at:

- `src/cpa_sim/examples/wust_gnlse_fiber_example.py`

Run it with:

```bash
python -m cpa_sim.examples.wust_gnlse_fiber_example --out artifacts/fiber-example --format svg
```

For configuration/units details, see `docs/examples/wust-gnlse-fiber-example.md`.

Canonical end-to-end 1560 nm chain example documentation is at:

- `docs/examples/canonical-1560nm-chain.md`


Toy amplifier A/B example documentation is available at:

- `docs/examples/toy-fiber-amp-spm.md`


## Outputs and provenance

`cpa-sim run ... --out <dir>` uses this canonical output layout:

- `metrics.json` (schema `cpa.metrics.v1`)
  - `overall`: aggregate flat metric map
  - `per_stage`: stage-grouped metric map
- `artifacts.json` (schema `cpa.artifacts.v1`)
  - `paths`: artifact-name to file-path map
- `stage_plots/`
  - `<stage>_time_intensity.svg`
  - `<stage>_spectrum.svg`
- `state_final.npz` (optional via `--dump-state-npz`)

A run returns a `StageResult` with deterministic `state`, `metrics`, and provenance metadata in `state.meta`.

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
