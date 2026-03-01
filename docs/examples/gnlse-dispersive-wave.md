# gnlse dispersive-wave showcase

This example recreates the doc-style dispersive-wave heatmaps (wavelength-vs-distance and delay-vs-distance)
using cpa-sim's existing output policy and artifact layout.

It is derived from the `gnlse-python` dispersive-wave / Raman showcase style (`test_raman` family), but uses the cpa-sim
`FiberStage` wrapper and canonical run outputs.

## Prerequisites

```bash
pip install -e .[dev,gnlse]
```

## Run

```bash
python -m cpa_sim.examples.gnlse_dispersive_wave_showcase --out out
```

## Output layout

After running, files are written under `out/` in canonical style:

- `out/metrics.json`
- `out/artifacts.json`
- `out/stage_plots/` (policy key `cpa.stage_plot_dir`)

Expected stage-level artifacts include:

- `out/stage_plots/fiber_dispersive_wave_z_traces.npz`
- `out/stage_plots/fiber_dispersive_wave_wavelength_vs_distance.png`
- `out/stage_plots/fiber_dispersive_wave_delay_vs_distance.png`

The NPZ contains the saved z-traces (`z_m`, `t_fs`, `at_zt_real`, `at_zt_imag`, and `w_rad_per_fs`) so the showcase can
regenerate plotting outputs without introducing a new artifact system.

## Notes

- The script uses the matplotlib `Agg` backend for headless environments.
- If the optional `gnlse` dependency is unavailable, the FiberStage backend will fail with the standard optional dependency message.
