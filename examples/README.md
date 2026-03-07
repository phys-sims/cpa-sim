# Examples

User-facing examples are implemented under `src/cpa_sim/examples/` and run via module entrypoints.

## Run examples

```bash
python -m cpa_sim.examples.wust_gnlse_fiber_example --out artifacts/fiber-example --format svg
python -m cpa_sim.examples.gnlse_dispersive_wave --outdir artifacts/gnlse-dispersive-wave
python -m cpa_sim.examples.spm_after_fiber_amp --out artifacts/spm-after-fiber-amp
python -m cpa_sim.examples.treacy_stage_validation
```

Top-level wrapper scripts were removed to keep a single source of truth.
