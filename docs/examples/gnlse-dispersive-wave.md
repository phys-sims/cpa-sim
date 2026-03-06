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

## Override plotting windows and heatmap scaling (CLI/policy)

You can keep stage code unchanged and override plotting behavior from a command-line wrapper by
passing `policy_overrides` into `run_pipeline_with_plot_policy(...)` and then feeding the merged
policy into `PlotWindowPolicy.from_policy_bag(...)` for post-processing heatmaps.

```bash
python - <<'PY'
from pathlib import Path

from cpa_sim.models import PlotWindowPolicy
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz
from cpa_sim.reporting import run_pipeline_with_plot_policy
from cpa_sim.examples.gnlse_dispersive_wave_showcase import DEFAULT_STAGE_NAME
from cpa_sim.examples.gnlse_dispersive_wave_showcase import PipelineConfig, RuntimeCfg
from cpa_sim.examples.gnlse_dispersive_wave_showcase import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PulseSpec,
    RamanCfg,
    WustGnlseNumericsCfg,
)

out_dir = Path("out-policy")
stage_plot_dir = out_dir / "stage_plots"

cfg = PipelineConfig(
    runtime=RuntimeCfg(seed=7),
    laser_gen=LaserGenCfg(
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="sech2",
                peak_power_w=1000,
                width_fs=50.0,
                center_wavelength_nm=835.0,
                n_samples=2048,
                time_window_fs=12500.0,
            )
        )
    ),
    stages=[
        FiberCfg(
            name=DEFAULT_STAGE_NAME,
            physics=FiberPhysicsCfg(
                length_m=0.15,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.11,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[-0.02, 0.000084]),
                raman=RamanCfg(model="blowwood"),
                self_steepening=True,
            ),
            numerics=WustGnlseNumericsCfg(backend="wust_gnlse", z_saves=2000, keep_full_solution=True),
        )
    ],
)

policy_overrides = {
    "cpa.plot.heatmap.coverage_quantile": 0.995,
    "cpa.plot.heatmap.pad_fraction": 0.03,
    "cpa.plot.heatmap.scale": "log",
    "cpa.plot.heatmap.dynamic_range_db": 45.0,
}

run_output = run_pipeline_with_plot_policy(
    cfg,
    stage_plot_dir=stage_plot_dir,
    policy_overrides=policy_overrides,
)
artifacts = dict(run_output.artifacts)
z_npz = Path(artifacts[f"{DEFAULT_STAGE_NAME}.z_traces_npz"])

plot_dispersive_wave_maps_from_npz(
    npz_path=z_npz,
    center_wavelength_nm=835.0,
    out_dir=stage_plot_dir,
    stem=DEFAULT_STAGE_NAME,
    plot_policy=PlotWindowPolicy.from_policy_bag(run_output.policy),
)
PY
```

This policy-first path lets you tighten windows and change heatmap normalization entirely from CLI
or wrapper policy values (`cpa.plot.*`), without modifying stage implementations.

## Notes

- The script uses the matplotlib `Agg` backend for headless environments.
- If the optional `gnlse` dependency is unavailable, the FiberStage backend will fail with the standard optional dependency message.
