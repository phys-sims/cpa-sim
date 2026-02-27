# WUST `gnlse` fiber example (Phase 7)

This example demonstrates a minimal, runnable fiber-only workflow:

1. create a **1550 nm, 1 ps (intensity FWHM) gaussian** input pulse,
2. run `FiberStage` with `numerics.backend="wust_gnlse"` and explicit Kerr + Raman settings,
3. save time-domain and spectral plots as vector graphics.

## Prerequisites

Install editable package + optional dependencies:

```bash
pip install -e .[dev,gnlse]
```

> `gnlse` is an optional dependency. If it is missing, the stage raises a clear runtime error with the install hint.

## Run

```bash
python -m cpa_sim.examples.wust_gnlse_fiber_example --out artifacts/fiber-example --format svg
```

Expected outputs:

- `artifacts/fiber-example/fiber_time_intensity.svg`
- `artifacts/fiber-example/fiber_spectrum.svg`

Use `--format pdf` if you prefer PDF vector output.

## Fiber config fields and units

The example uses the Strategy-B config split:

- `fiber.physics`: stable physical model parameters,
- `fiber.numerics`: backend-specific solver/grid settings.

### `FiberPhysicsCfg`

- `length_m`: fiber length in meters.
- `loss_db_per_m`: attenuation in dB/m.
- `gamma_1_per_w_m`: nonlinear coefficient in 1/(W·m).
- `dispersion.kind="taylor"` with `betas_psn_per_m`: β₂, β₃, ... in psⁿ/m.
- optional `raman` and `self_steepening` toggles.

### `WustGnlseNumericsCfg`

- `backend="wust_gnlse"` selects the WUST-FOG adapter.
- `grid_policy`: `use_state`, `force_pow2`, or `force_resolution`.
- optional solver controls: `z_saves`, `method`, `rtol`, `atol`.
- artifact toggles: `keep_full_solution`, `keep_aw`, `record_backend_version`.

## Backend selection

- `numerics.backend="toy_phase"` gives a lightweight deterministic baseline.
- `numerics.backend="wust_gnlse"` executes the external solver wrapper.

Backend dispatch occurs inside `FiberStage` and is isolated from the public stage config shape.

## Normalization expectations

The WUST backend expects and emits envelope amplitudes in **sqrt(W)** so that:

- instantaneous power is `|A(t)|^2` in watts,
- pulse energy is `∫|A(t)|^2 dt` with `dt` in seconds.

The stage records this contract in state metadata:

- `state.meta["pulse"]["field_units"] == "sqrt(W)"`
- `state.meta["pulse"]["power_is_absA2_W"] is True`

The example plots are intentionally labeled as *derived from* `|A|^2`/`|Aw|^2` to avoid over-claiming absolute calibration when upstream pulse generation choices are modified.


## Example physics settings (current)

- Pulse: gaussian, `center_wavelength_nm=1550`, `width_fs=1000`, `amplitude=35`, `n_samples=1024`, `time_window_fs=12000`.
- Fiber: `length_m=0.25`, `gamma_1_per_w_m=2.0`, `dispersion.betas_psn_per_m=[-0.02]`.
- Raman: `raman.kind="wust"`, `raman.model="blowwood"`.

These values are tuned to clearly demonstrate nonlinear temporal/spectral evolution in a compact example run.
