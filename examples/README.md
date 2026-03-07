# Examples

User-facing examples are implemented under `src/cpa_sim/examples/` and run via module entrypoints.

## Run examples

```bash
python -m cpa_sim.examples.simple_fiber_dispersion --out artifacts/simple-fiber-dispersion --format svg
python -m cpa_sim.examples.wave_breaking_raman --outdir artifacts/wave-breaking-raman
python -m cpa_sim.examples.fiber_amp_spm --out artifacts/fiber-amp-spm
python -m cpa_sim.examples.treacy_stage_validation
python -m cpa_sim.examples.end_to_end_1560nm --ci-safe --out artifacts/end-to-end-1560nm-ci
```

Top-level wrapper scripts were removed to keep a single source of truth.
