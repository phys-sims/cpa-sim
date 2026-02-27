# PulseSpec configuration guide

This page defines how `PulseSpec` inputs map to the simulator's canonical internal representation.

## Canonical internal meaning

- `width_fs` is the **pulse intensity FWHM** in femtoseconds (fs), not field FWHM.
- The complex envelope field is normalized in **sqrt(W)**.
- Instantaneous power is computed as `|E(t)|^2` in **W**.

These conventions are stable across stages (`laser_gen` → free-space → fiber → amp) so downstream metrics remain comparable.

## User input options for pulse normalization

Use one of these user-facing input modes:

1. `avg_power_w` + `rep_rate_mhz`
   - Best for lab workflows where average output power and repetition rate are known.
   - Relationship used internally: `pulse_energy_j = avg_power_w / (rep_rate_mhz * 1e6)`.

2. `pulse_energy_j`
   - Best when single-pulse energy is measured directly.

3. `peak_power_w`
   - Best when peak-power target is known or intentionally prescribed.

All three modes resolve to the same internal envelope normalization (`sqrt(W)`), so stage physics and metrics are consistent once initialized.

## Legacy `amplitude` input (deprecated)

`amplitude` is still accepted for compatibility, but it is **deprecated**.

- Meaning: `amplitude` is a field scaling in **sqrt(W)**.
- Equivalent peak power mapping: `peak_power_w = amplitude^2`.
- Why it is being replaced: `avg_power_w`, `pulse_energy_j`, and `peak_power_w` are more directly measurable in lab practice and reduce unit/sign confusion.

For new configs, migrate to `avg_power_w` + `rep_rate_mhz`, `pulse_energy_j`, or `peak_power_w`.

## Autocorrelation input

`intensity_autocorr_fwhm_fs` means the **intensity autocorrelation FWHM** in fs.

To convert autocorrelation FWHM to pulse intensity FWHM (`width_fs`), use:

- Gaussian pulses:
  - `FWHM_pulse = FWHM_AC / sqrt(2)`
- Sech² pulses:
  - `FWHM_pulse = FWHM_AC / 1.543 ≈ 0.648 * FWHM_AC`

> ⚠️ **Important warning**
>
> Only use `intensity_autocorr_fwhm_fs` if your number is the *raw autocorrelation* FWHM.
> If you already multiplied by `0.648` (sech2) or `0.707` (Gaussian), then use `width_fs` directly.
