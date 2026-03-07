# Fiber Amp SPM

This example shows nonlinear phase accumulation after a fiber amplifier wrap stage.

## Physics config (minimal)

```python
from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberAmpWrapCfg,
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
                width_fs=7000.0,
                avg_power_w=0.3,
                rep_rate_mhz=1115.0,
                center_wavelength_nm=1560.0,
                n_samples=2048,
                time_window_fs=100000.0,
            )
        )
    ),
    stages=[
        FiberAmpWrapCfg(
            name="fiber_amp_spm",
            power_out_w=4.5,
            physics=FiberPhysicsCfg(
                length_m=14.0,
                n2_m2_per_w=2.6e-20,
                aeff_m2=4.18879020478639e-12,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(backend="wust_gnlse", z_saves=64),
        )
    ],
)
```

## Run

```bash
python -m cpa_sim.examples.fiber_amp_spm
```

## Expected artifacts

- `artifacts/fiber-amp-spm/summary.json`
- `artifacts/fiber-amp-spm/fiber_amp_spm_time_intensity.svg`
- `artifacts/fiber-amp-spm/fiber_amp_spm_spectrum.svg`
- `artifacts/fiber-amp-spm/metrics_time_intensity_overlay.svg`
- `artifacts/fiber-amp-spm/metrics_spectrum_overlay.svg`

## Advanced options

```python
from pathlib import Path
from cpa_sim.examples.fiber_amp_spm import run_example

summary = run_example(out_dir=Path("my-output/fiber-amp"))
print(summary["metrics"]["cpa.metrics.summary.energy_au"])
```

## What to change for your experiment

| Parameter | Physical meaning | Typical direction |
| --- | --- | --- |
| `power_out_w` | Amplifier target average output power | Increase to drive stronger nonlinear broadening. |
| `length_m` | Nonlinear interaction length | Longer fiber raises accumulated nonlinear phase. |
| `n2_m2_per_w`, `aeff_m2` | Kerr nonlinearity and mode area | Higher `n2` or lower `aeff` strengthens SPM. |
| `width_fs` | Input pulse duration | Shorter pulses tend to broaden spectrally faster. |
