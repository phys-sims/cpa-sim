# Wave Breaking Raman

This is the canonical nonlinear fiber example: higher-order dispersion + Raman + self-steepening with WUST-compatible delay/wavelength evolution maps.

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
    RamanCfg,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)

cfg = PipelineConfig(
    runtime=RuntimeCfg(seed=7),
    laser_gen=LaserGenCfg(
        spec=LaserSpec(
            pulse=PulseSpec(
                center_wavelength_nm=835.0,
                shape="sech2",
                width_fs=50.284,
                peak_power_w=10000.0,
                n_samples=8192,
                time_window_fs=12500.0,
            )
        )
    ),
    stages=[
        FiberCfg(
            name="wave_breaking_raman",
            physics=FiberPhysicsCfg(
                length_m=0.15,
                gamma_1_per_w_m=0.11,
                self_steepening=True,
                dispersion=DispersionTaylorCfg(
                    betas_psn_per_m=[
                        -11.830e-3,
                        8.1038e-5,
                        -9.5205e-8,
                        2.0737e-10,
                        -5.3943e-13,
                        1.3486e-15,
                        -2.5495e-18,
                        3.0524e-21,
                        -1.7140e-24,
                    ]
                ),
                raman=RamanCfg(model="blowwood"),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                z_saves=400,
                keep_full_solution=True,
            ),
        )
    ],
)
```

## Run

```bash
python -m cpa_sim.examples.wave_breaking_raman
```

## Expected artifacts

- `artifacts/wave-breaking-raman/wave_breaking_raman_z_traces.npz`
- `artifacts/wave-breaking-raman/wave_breaking_raman_wavelength_vs_distance_linear.png`
- `artifacts/wave-breaking-raman/wave_breaking_raman_wavelength_vs_distance_log.png`
- `artifacts/wave-breaking-raman/wave_breaking_raman_delay_vs_distance_linear.png`
- `artifacts/wave-breaking-raman/wave_breaking_raman_delay_vs_distance_log.png`

## Advanced options

Use API mode when you want lighter sweeps or different Raman model:

```python
from pathlib import Path
from cpa_sim.examples.wave_breaking_raman import run_example

run_example(
    out_dir=Path("my-output/wave-breaking"),
    n_samples=2048,
    z_saves=96,
    raman_model="hollenbeck",
)
```

To regenerate docs assets:

```bash
python scripts/build_docs_assets.py --mode ci
```

## What to change for your experiment

| Parameter | Physical meaning | Typical direction |
| --- | --- | --- |
| `betas_psn_per_m` | High-order dispersion phase matching | Adjust to move dispersive-wave wavelength. |
| `raman_model` | Raman response model family | Compare model sensitivity for red/blue-shift dynamics. |
| `self_steepening` | Optical shock term | Enable for stronger wave-breaking structure. |
| `n_samples`, `z_saves` | Temporal/z resolution | Increase for cleaner maps and tighter regression stability. |
