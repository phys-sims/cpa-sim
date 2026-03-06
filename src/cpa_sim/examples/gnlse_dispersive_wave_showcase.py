from __future__ import annotations

import argparse
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
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz
from cpa_sim.reporting import run_pipeline_with_plot_policy, write_json

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

    run_output = run_pipeline_with_plot_policy(cfg, stage_plot_dir=stage_plot_dir)
    policy = run_output.policy
    artifacts = dict(run_output.artifacts)
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

    write_json(out_dir / "metrics.json", run_output.metrics_payload)
    write_json(out_dir / "artifacts.json", run_output.artifacts_payload | {"paths": artifacts})

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
