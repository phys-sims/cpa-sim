# Wave Breaking Raman

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
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman
```

Quick mode:

```bash
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman --fast
```

Optional Raman variants:

```bash
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman --raman-model blowwood
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman --raman-model hollenbeck
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman --raman-model none
```

## Output artifacts

Expected files under `--outdir`:

- `wave_breaking_raman_z_traces.npz`
- `wave_breaking_raman_wavelength_vs_distance_linear.png`
- `wave_breaking_raman_wavelength_vs_distance_log.png`
- `wave_breaking_raman_delay_vs_distance_linear.png`
- `wave_breaking_raman_delay_vs_distance_log.png`

## Docs asset generation

To regenerate the docs SVG set for this example:

```bash
python scripts/build_docs_assets.py --mode ci
```

For PR-safe docs builds:

```bash
python scripts/build_docs_assets.py --mode ultra-fast --allow-missing-gnlse
```
