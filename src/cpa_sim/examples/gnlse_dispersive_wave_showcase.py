from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PlotWindowPolicy,
    PulseSpec,
    RamanCfg,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.pipeline import run_pipeline
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz

DEFAULT_OUT_DIR = Path("out")
DEFAULT_STAGE_NAME = "fiber_dispersive_wave"


def run_showcase(*, out_dir: Path, seed: int = 7) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_plot_dir = out_dir / "stage_plots"

    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
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
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=2000,
                    keep_full_solution=True,
                ),
            )
        ],
    )

    policy = {
        "cpa.emit_stage_plots": True,
        "cpa.stage_plot_dir": str(stage_plot_dir),
        "cpa.plot.line.threshold_fraction": 1e-3,
        "cpa.plot.line.min_support_width": 0.0,
        "cpa.plot.line.pad_fraction": 0.05,
        "cpa.plot.heatmap.coverage_quantile": 0.999,
        "cpa.plot.heatmap.pad_fraction": 0.10,
        "cpa.plot.heatmap.fallback_behavior": "full_axis",
    }
    result = run_pipeline(cfg, policy=policy)

    artifacts = {**result.artifacts, **result.state.artifacts}
    z_npz = Path(artifacts[f"{DEFAULT_STAGE_NAME}.z_traces_npz"])

    plots = plot_dispersive_wave_maps_from_npz(
        npz_path=z_npz,
        center_wavelength_nm=835.0,
        out_dir=stage_plot_dir,
        stem=DEFAULT_STAGE_NAME,
        plot_policy=PlotWindowPolicy.from_policy_bag(policy),
    )

    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_linear"] = str(
        plots.wavelength_linear
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_log"] = str(plots.wavelength_log)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_linear"] = str(plots.delay_linear)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_log"] = str(plots.delay_log)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance"] = str(plots.wavelength_log)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance"] = str(plots.delay_log)

    metrics_payload = {
        "schema_version": "cpa.metrics.v1",
        "overall": result.metrics,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True) + "\n"
    )
    (out_dir / "artifacts.json").write_text(
        json.dumps(
            {"schema_version": "cpa.artifacts.v1", "paths": artifacts}, indent=2, sort_keys=True
        )
        + "\n"
    )

    return artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate gnlse dispersive-wave showcase plots.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    artifacts = run_showcase(out_dir=args.out, seed=args.seed)
    for key in (
        f"{DEFAULT_STAGE_NAME}.z_traces_npz",
        f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_linear",
        f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_log",
        f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_linear",
        f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_log",
    ):
        print(f"{key}: {artifacts[key]}")


if __name__ == "__main__":
    main()
