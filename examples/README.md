# Examples

User-facing runnable scripts for reproducing canonical `cpa-sim` scenarios.

## Dispersive-wave generation

```bash
python examples/gnlse_dispersive_wave.py --outdir artifacts/example-dispersive-wave
```

The script runs the WUST `gnlse` fiber backend and writes publication-oriented figures:

- Input/output spectrum comparison (`z=0` vs `z=L`)
- Wavelength-vs-distance evolution heatmap
- Delay-vs-distance evolution heatmap
