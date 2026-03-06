# Examples

User-facing wrappers for canonical scenarios. Source implementations are centralized in `src/cpa_sim/examples/`.

## Dispersive-wave generation

```bash
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/example-dispersive-wave
```

The script runs the WUST `gnlse` fiber backend and writes publication-oriented figures:

- Input/output spectrum comparison (`z=0` vs `z=L`)
- Wavelength-vs-distance evolution heatmap
- Delay-vs-distance evolution heatmap

## SPM after fiber amp stage

```bash
python -m cpa_sim.examples.spm_after_fiber_amp --out artifacts/example-spm-after-amp
```

This script demonstrates nonlinear self-phase modulation (SPM) through a `FiberAmpWrapStage` using:

- `gamma = 0.025 1/(W·m)`
- fiber length `L = 2 m`
- input pulse: `sech²`, `7 ps` FWHM, `0.3 W` average power
- amplifier target output: `4.5 W` average power
- repetition rate: `1.115 GHz`
