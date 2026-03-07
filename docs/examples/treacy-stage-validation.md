# Treacy Stage Validation

This example validates free-space phase-only dispersion behavior and Treacy geometry parity.

The convention is:

- `gdd_fs2 = d2phi/domega2|omega0`
- `tod_fs3 = d3phi/domega3|omega0`
- `phi(Delta omega) = +0.5*gdd_fs2*Delta omega^2 + (1/6)*tod_fs3*Delta omega^3`

## Physics config (minimal)

```python
from cpa_sim.models.config import PhaseOnlyDispersionCfg, TreacyGratingPairCfg

poly = PhaseOnlyDispersionCfg(name="poly_gdd", gdd_fs2=8.5e4, tod_fs3=0.0)
treacy = TreacyGratingPairCfg(
    name="treacy",
    line_density_lpmm=1200.0,
    incidence_angle_deg=34.0,
    separation_um=115_000.0,
    wavelength_nm=1030.0,
    include_tod=True,
)
```

## Run

```bash
python -m cpa_sim.examples.treacy_stage_validation
```

## Expected artifacts

PNG outputs are written to `docs/assets/treacy_validation/`, including:

- `phi_vs_w.png`
- `group_delay_vs_w.png`
- `d2phi_vs_w.png`
- `intensity_time_before_after.png`
- `spectrum_before_after.png`
- `treacy_vs_poly_intensity_overlay.png`
- `treacy_vs_poly_spectrum_overlay.png`

## Validation plots

![Spectral phase vs offset frequency](../assets/treacy_validation/phi_vs_w.png)
![Group delay vs offset frequency](../assets/treacy_validation/group_delay_vs_w.png)
![Second derivative of spectral phase](../assets/treacy_validation/d2phi_vs_w.png)
![Time-domain intensity before/after stretcher and compressor](../assets/treacy_validation/intensity_time_before_after.png)
![Spectrum before/after phase-only stages](../assets/treacy_validation/spectrum_before_after.png)
![Treacy vs matched polynomial intensity overlay](../assets/treacy_validation/treacy_vs_poly_intensity_overlay.png)

## What to change for your experiment

| Parameter | Physical meaning | Typical direction |
| --- | --- | --- |
| `line_density_lpmm` | Grating groove density | Changes Treacy GDD/TOD scale. |
| `separation_um` | Grating spacing | Primary control of compression amount. |
| `include_tod` | Include third-order dispersion term | Toggle TOD impact on pulse shape. |
| `n_samples`, `time_window_fs` (laser init) | Validation grid fidelity | Increase for cleaner derivative recovery. |
