# End-to-End 1560nm

This example runs a full CPA chain at 1560 nm:

1. regular-dispersion fiber broadening,
2. fiber amplifier wrap,
3. Treacy compressor.

## Physics config (minimal)

```python
from cpa_sim.examples.end_to_end_1560nm import build_config

cfg = build_config(seed=1560, ci_safe=False)
```

The built config contains:

- laser init (`sech2`, 1560 nm),
- `fiber_regular_disp_1560nm` stage,
- `fiber_amp_spm` stage,
- `treacy_compressor` stage.

## Run

```bash
python -m cpa_sim.examples.end_to_end_1560nm
```

## Expected artifacts

- `artifacts/end-to-end-1560nm/run_summary.json`
- stage SVG plots in `artifacts/end-to-end-1560nm/stage-plots/`
- metrics overlays from the metrics stage (`metrics_time_intensity_overlay.svg`, `metrics_spectrum_overlay.svg`)

## Advanced options

Use API mode for lighter CI-style runs:

```python
from pathlib import Path
from cpa_sim.examples.end_to_end_1560nm import run_example

run_example(
    out_dir=Path("my-output/end-to-end-ci"),
    plot_dir=Path("my-output/end-to-end-ci/stage-plots"),
    seed=1560,
    ci_safe=True,
)
```

## What to change for your experiment

| Parameter | Physical meaning | Typical direction |
| --- | --- | --- |
| `fiber_length_m` (regular stage) | Linear broadening path length | Increase for more dispersive stretch. |
| `power_out_w` (amp stage) | Amplifier output power target | Increase for stronger nonlinear phase. |
| `separation_um` (Treacy) | Compressor dispersion tuning | Adjust to recompress broadened pulse. |
| `ci_safe` | Reduced numerical workload profile | Use `True` for smoke runs, `False` for full outputs. |
