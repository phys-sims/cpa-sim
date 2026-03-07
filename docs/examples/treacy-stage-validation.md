# Treacy Stage Validation

This page documents reproducible validation artifacts for the free-space dispersion stage.
The model used here is a **phase-only spectral operator on the envelope**, where the stage applies `phi(Delta omega)` directly on the offset-frequency grid and the simulator `w` axis is `Delta omega` (not absolute optical carrier frequency).

The dispersion coefficients follow the physical-derivative convention: `gdd_fs2 = d2phi/domega2|omega0`, `tod_fs3 = d3phi/domega3|omega0`, and `phi(Delta omega) = +0.5*gdd_fs2*Delta omega^2 + (1/6)*tod_fs3*Delta omega^3`.

## What was validated

- Treacy GDD/TOD scalar correctness from geometry (covered by existing tests).
- Correct application of \(\phi(\Delta\omega)\) to the field (new derivation/plot evidence).
- Analytic Gaussian broadening benchmark under phase-only dispersion.
- Treacy vs `PhaseOnlyDispersion` equivalence when TOD is enabled and coefficients are matched.

## Validation plots

### Spectral phase and derivatives

![Spectral phase vs offset frequency](../assets/treacy_validation/phi_vs_w.png)

![Group delay vs offset frequency](../assets/treacy_validation/group_delay_vs_w.png)

![Second derivative of spectral phase](../assets/treacy_validation/d2phi_vs_w.png)

### Time and spectral domain pulse behavior

![Time-domain intensity before/after stretcher and compressor](../assets/treacy_validation/intensity_time_before_after.png)

![Spectrum before/after phase-only stages](../assets/treacy_validation/spectrum_before_after.png)

### Treacy vs polynomial phase-only equivalence

![Treacy vs matched polynomial intensity overlay](../assets/treacy_validation/treacy_vs_poly_intensity_overlay.png)

## How to regenerate

From the repository root:

```bash
python -m cpa_sim.examples.treacy_stage_validation
```

The script writes PNG artifacts to `docs/assets/treacy_validation/` and prints a short summary
including RMS durations and recovered GDD/TOD estimates from numerical derivatives.
