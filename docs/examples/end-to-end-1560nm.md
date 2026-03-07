# End-to-End 1560nm

This example runs a deterministic 1560 nm CPA chain using solver-backed fiber stages:

1. linear broadening in regular-dispersion fiber,
2. fiber amplifier wrap with target output power,
3. Treacy compressor phase action.

> Dependency note: this example requires optional WUST-FOG `gnlse` support (`pip install -e .[gnlse]`).

## Run

CI-safe mode:

```bash
python -m cpa_sim.examples.end_to_end_1560nm \
  --ci-safe \
  --out artifacts/end-to-end-1560nm-ci \
  --plot-dir artifacts/end-to-end-1560nm-ci/stage-plots
```

Larger run:

```bash
python -m cpa_sim.examples.end_to_end_1560nm \
  --out artifacts/end-to-end-1560nm \
  --plot-dir artifacts/end-to-end-1560nm/stage-plots \
  --seed 1560
```

## Outputs

The script writes:

- `run_summary.json`
- stage SVG plots in `--plot-dir`

Typical stage plot files include:

- `laser_init_time_intensity.svg`
- `fiber_regular_disp_1560nm_time_intensity.svg`
- `fiber_amp_spm_time_intensity.svg`
- `treacy_compressor_time_intensity.svg`
