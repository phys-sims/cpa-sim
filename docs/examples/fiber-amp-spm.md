# Fiber Amp SPM

This example demonstrates nonlinear phase accumulation after a fiber amplifier wrap stage.

It uses:

- `FiberAmpWrapCfg` with `power_out_w=4.5`,
- nonlinear fiber inputs (`n2_m2_per_w`, `aeff_m2`),
- a 1560 nm sech2 input pulse.

## Prerequisites

```bash
pip install -e .[dev,gnlse]
```

## Run

```bash
python -m cpa_sim.examples.fiber_amp_spm --out artifacts/fiber-amp-spm
```

## Output artifacts

- `artifacts/fiber-amp-spm/summary.json`
- `artifacts/fiber-amp-spm/fiber_amp_spm_time_intensity.svg`
- `artifacts/fiber-amp-spm/fiber_amp_spm_spectrum.svg`
