# WUST `gnlse` simple fiber-dispersion example

This example is the lightweight linear-dispersion sanity check.

Workflow:

1. initialize a 1550 nm pulse,
2. propagate with `numerics.backend="wust_gnlse"`,
3. keep nonlinearity disabled (`gamma_1_per_w_m=0.0`) and use nonzero Taylor dispersion,
4. emit clear before/after time and spectrum plots.

## Prerequisites

```bash
pip install -e .[dev,gnlse]
```

## Run

```bash
python -m cpa_sim.examples.wust_gnlse_fiber_example --out artifacts/fiber-example --format svg
```

## Expected outputs

- `artifacts/fiber-example/laser_init_time_intensity.svg`
- `artifacts/fiber-example/laser_init_spectrum.svg`
- `artifacts/fiber-example/fiber_example_time_intensity.svg`
- `artifacts/fiber-example/fiber_example_spectrum.svg`

## Current physics settings

- Pulse: `shape="sech2"`, `center_wavelength_nm=1550.0`, `width_fs=1000.0`, `peak_power_w=5.0`
- Grid: `n_samples=1024`, `time_window_fs=12000.0`
- Fiber: `length_m=0.3`, `loss_db_per_m=0.0`, `gamma_1_per_w_m=0.0`
- Dispersion: `DispersionTaylorCfg(betas_psn_per_m=[0.03])`
- Numerics: `z_saves=32`, `keep_full_solution=False`
