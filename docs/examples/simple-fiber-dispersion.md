# Simple Fiber Dispersion

This example is the minimal linear-fiber sanity check: phase-only broadening from Taylor dispersion with nonlinearity disabled.

## Physics config (minimal)

```python
from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)

cfg = PipelineConfig(
    runtime=RuntimeCfg(seed=7),
    laser_gen=LaserGenCfg(
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="sech2",
                peak_power_w=5.0,
                width_fs=1000.0,
                center_wavelength_nm=1550.0,
                n_samples=1024,
                time_window_fs=12000.0,
            )
        )
    ),
    stages=[
        FiberCfg(
            name="simple_fiber_dispersion",
            physics=FiberPhysicsCfg(
                length_m=0.3,
                gamma_1_per_w_m=0.0,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.03]),
            ),
            numerics=WustGnlseNumericsCfg(backend="wust_gnlse", z_saves=32),
        )
    ],
)
```

## Run

```bash
python -m cpa_sim.examples.simple_fiber_dispersion
```

## Expected artifacts

- `artifacts/simple-fiber-dispersion/laser_init_time_intensity.svg`
- `artifacts/simple-fiber-dispersion/laser_init_spectrum.svg`
- `artifacts/simple-fiber-dispersion/simple_fiber_dispersion_time_intensity.svg`
- `artifacts/simple-fiber-dispersion/simple_fiber_dispersion_spectrum.svg`
- `artifacts/simple-fiber-dispersion/metrics_time_intensity_overlay.svg`
- `artifacts/simple-fiber-dispersion/metrics_spectrum_overlay.svg`

## Advanced options

Use Python API if you want different output location:

```python
from pathlib import Path
from cpa_sim.examples.simple_fiber_dispersion import run_example

run_example(out_dir=Path("my-output/simple-fiber"), plot_format="svg")
```

## What to change for your experiment

| Parameter | Physical meaning | Typical direction |
| --- | --- | --- |
| `width_fs` | Input pulse duration | Smaller values increase spectral spread. |
| `betas_psn_per_m` | Dispersion polynomial terms | Larger magnitude increases temporal reshaping. |
| `length_m` | Fiber interaction length | Longer fiber increases accumulated dispersive phase. |
| `n_samples`, `time_window_fs` | Numerical grid fidelity/window | Increase when tails or aliasing appear in plots. |
