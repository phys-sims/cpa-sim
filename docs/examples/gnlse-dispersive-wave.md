# GNLS dispersive-wave example

This is the single user-facing wave-breaking + Raman sanity-check example.

It runs a short 835 nm `sech2` pulse through nonlinear fiber with higher-order
Taylor dispersion, Raman response, and self-steepening enabled so short-wavelength
dispersive-wave content appears in the output maps.

## Prerequisites

```bash
pip install -e .[dev,gnlse]
```

## Run

```bash
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave
```

Quick mode:

```bash
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave --fast
```

Optional Raman variants:

```bash
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave --raman-model blowwood
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave --raman-model hollenbeck
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave --raman-model none
```

## Output artifacts

Expected files under `--outdir`:

- `fiber_dispersive_wave_z_traces.npz`
- `fiber_dispersive_wave_wavelength_vs_distance_linear.png`
- `fiber_dispersive_wave_wavelength_vs_distance_log.png`
- `fiber_dispersive_wave_delay_vs_distance_linear.png`
- `fiber_dispersive_wave_delay_vs_distance_log.png`

## Docs asset generation

To regenerate the docs SVG set for this example:

```bash
python scripts/build_docs_assets.py --mode ci
```

For PR-safe docs builds:

```bash
python scripts/build_docs_assets.py --mode ultra-fast --allow-missing-gnlse
```
