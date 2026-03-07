from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from cpa_sim.models import (
    DispersionInterpolationCfg,
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RamanCfg,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz
from cpa_sim.plotting.common import load_pyplot
from cpa_sim.plotting.dispersive_wave import (
    _load_npz_traces,
    _prepare_wust_map_data,
    _render_wust_delay_map,
    _render_wust_wavelength_map,
)
from cpa_sim.reporting import run_pipeline_with_plot_policy, write_json

DEFAULT_OUT_DIR = Path("out")
DEFAULT_STAGE_NAME = "fiber_dispersive_wave"
_TAYLOR_STAGE_NAME = f"{DEFAULT_STAGE_NAME}_taylor"
_INTERP_STAGE_NAME = f"{DEFAULT_STAGE_NAME}_interpolation"
_TIME_RANGE_PS = (-0.5, 5.0)
_WL_RANGE_NM = (400.0, 1400.0)


def _interpolation_dispersion_cfg() -> DispersionInterpolationCfg:
    lambdas_nm = np.linspace(700.0, 1000.0, 80)
    offsets = lambdas_nm - 835.0
    neff = 1.45 + 1e-4 * offsets + 1e-7 * offsets**2
    return DispersionInterpolationCfg(
        effective_indices=neff.tolist(),
        lambdas_nm=lambdas_nm.tolist(),
        central_wavelength_nm=835.0,
    )


def _build_cfg(
    *,
    seed: int,
    stage_name: str,
    dispersion: DispersionTaylorCfg | DispersionInterpolationCfg,
) -> PipelineConfig:
    return PipelineConfig(
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
                name=stage_name,
                physics=FiberPhysicsCfg(
                    length_m=0.15,
                    loss_db_per_m=0.0,
                    gamma_1_per_w_m=0.11,
                    dispersion=dispersion,
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


def _plot_combined_comparison(
    *,
    taylor_npz: Path,
    interpolation_npz: Path,
    out_path: Path,
    center_wavelength_nm: float,
) -> Path:
    taylor_z_m, taylor_t_fs, taylor_w_rad_per_fs, taylor_at_zt, taylor_aw_zw = _load_npz_traces(
        npz_path=taylor_npz
    )
    interp_z_m, interp_t_fs, interp_w_rad_per_fs, interp_at_zt, interp_aw_zw = _load_npz_traces(
        npz_path=interpolation_npz
    )
    taylor_data = _prepare_wust_map_data(
        at_zt=taylor_at_zt,
        z_m=taylor_z_m,
        t_fs=taylor_t_fs,
        w_rad_per_fs=taylor_w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        aw_zw=taylor_aw_zw,
        time_range_ps=_TIME_RANGE_PS,
        wl_range_nm=_WL_RANGE_NM,
    )
    interpolation_data = _prepare_wust_map_data(
        at_zt=interp_at_zt,
        z_m=interp_z_m,
        t_fs=interp_t_fs,
        w_rad_per_fs=interp_w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        aw_zw=interp_aw_zw,
        time_range_ps=_TIME_RANGE_PS,
        wl_range_nm=_WL_RANGE_NM,
    )

    plt = load_pyplot()
    fig, axes = plt.subplots(2, 2, figsize=(15, 7))
    _render_wust_wavelength_map(ax=axes[0, 0], map_data=taylor_data, scale="linear")
    _render_wust_wavelength_map(ax=axes[0, 1], map_data=interpolation_data, scale="linear")
    _render_wust_delay_map(ax=axes[1, 0], map_data=taylor_data, scale="linear")
    _render_wust_delay_map(ax=axes[1, 1], map_data=interpolation_data, scale="linear")

    axes[0, 0].set_title("Results for Taylor expansion")
    axes[0, 1].set_title("Results for interpolation")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    return out_path


def run_showcase(*, out_dir: Path, seed: int = 7) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_plot_dir = out_dir / "stage_plots"

    taylor_cfg = _build_cfg(
        seed=seed,
        stage_name=_TAYLOR_STAGE_NAME,
        dispersion=DispersionTaylorCfg(betas_psn_per_m=[-0.02, 0.000084]),
    )
    interpolation_cfg = _build_cfg(
        seed=seed,
        stage_name=_INTERP_STAGE_NAME,
        dispersion=_interpolation_dispersion_cfg(),
    )

    taylor_run = run_pipeline_with_plot_policy(taylor_cfg, stage_plot_dir=stage_plot_dir)
    interpolation_run = run_pipeline_with_plot_policy(
        interpolation_cfg, stage_plot_dir=stage_plot_dir
    )
    artifacts = {**taylor_run.artifacts, **interpolation_run.artifacts}

    taylor_npz = Path(artifacts[f"{_TAYLOR_STAGE_NAME}.z_traces_npz"])
    interpolation_npz = Path(artifacts[f"{_INTERP_STAGE_NAME}.z_traces_npz"])

    taylor_plots = plot_dispersive_wave_maps_from_npz(
        npz_path=taylor_npz,
        center_wavelength_nm=835.0,
        out_dir=stage_plot_dir,
        stem=_TAYLOR_STAGE_NAME,
        compat_mode="wust",
        time_range_ps=_TIME_RANGE_PS,
        wl_range_nm=_WL_RANGE_NM,
    )
    interpolation_plots = plot_dispersive_wave_maps_from_npz(
        npz_path=interpolation_npz,
        center_wavelength_nm=835.0,
        out_dir=stage_plot_dir,
        stem=_INTERP_STAGE_NAME,
        compat_mode="wust",
        time_range_ps=_TIME_RANGE_PS,
        wl_range_nm=_WL_RANGE_NM,
    )

    artifacts[f"{_TAYLOR_STAGE_NAME}.plot_wavelength_vs_distance_linear"] = str(
        taylor_plots.wavelength_linear
    )
    artifacts[f"{_TAYLOR_STAGE_NAME}.plot_wavelength_vs_distance_log"] = str(
        taylor_plots.wavelength_log
    )
    artifacts[f"{_TAYLOR_STAGE_NAME}.plot_delay_vs_distance_linear"] = str(
        taylor_plots.delay_linear
    )
    artifacts[f"{_TAYLOR_STAGE_NAME}.plot_delay_vs_distance_log"] = str(taylor_plots.delay_log)

    artifacts[f"{_INTERP_STAGE_NAME}.plot_wavelength_vs_distance_linear"] = str(
        interpolation_plots.wavelength_linear
    )
    artifacts[f"{_INTERP_STAGE_NAME}.plot_wavelength_vs_distance_log"] = str(
        interpolation_plots.wavelength_log
    )
    artifacts[f"{_INTERP_STAGE_NAME}.plot_delay_vs_distance_linear"] = str(
        interpolation_plots.delay_linear
    )
    artifacts[f"{_INTERP_STAGE_NAME}.plot_delay_vs_distance_log"] = str(
        interpolation_plots.delay_log
    )

    combined_path = _plot_combined_comparison(
        taylor_npz=taylor_npz,
        interpolation_npz=interpolation_npz,
        out_path=stage_plot_dir / f"{DEFAULT_STAGE_NAME}_dispersion_comparison.png",
        center_wavelength_nm=835.0,
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_dispersion_comparison"] = str(combined_path)

    # Keep the original stage-level aliases mapped to the Taylor case for backward compatibility.
    artifacts[f"{DEFAULT_STAGE_NAME}.z_traces_npz"] = str(taylor_npz)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_linear"] = str(
        taylor_plots.wavelength_linear
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_log"] = str(
        taylor_plots.wavelength_log
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_linear"] = str(
        taylor_plots.delay_linear
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_log"] = str(taylor_plots.delay_log)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance"] = str(
        taylor_plots.wavelength_log
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance"] = str(taylor_plots.delay_log)

    write_json(
        out_dir / "metrics.json",
        {
            "schema_version": "cpa.metrics.v1",
            "cases": {
                "taylor": taylor_run.metrics_payload,
                "interpolation": interpolation_run.metrics_payload,
            },
        },
    )
    write_json(
        out_dir / "artifacts.json",
        {
            "schema_version": "cpa.artifacts.v1",
            "paths": artifacts,
        },
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
        f"{_TAYLOR_STAGE_NAME}.z_traces_npz",
        f"{_INTERP_STAGE_NAME}.z_traces_npz",
        f"{DEFAULT_STAGE_NAME}.plot_dispersion_comparison",
        f"{_TAYLOR_STAGE_NAME}.plot_wavelength_vs_distance_linear",
        f"{_TAYLOR_STAGE_NAME}.plot_wavelength_vs_distance_log",
        f"{_TAYLOR_STAGE_NAME}.plot_delay_vs_distance_linear",
        f"{_TAYLOR_STAGE_NAME}.plot_delay_vs_distance_log",
        f"{_INTERP_STAGE_NAME}.plot_wavelength_vs_distance_linear",
        f"{_INTERP_STAGE_NAME}.plot_wavelength_vs_distance_log",
        f"{_INTERP_STAGE_NAME}.plot_delay_vs_distance_linear",
        f"{_INTERP_STAGE_NAME}.plot_delay_vs_distance_log",
    ):
        print(f"{key}: {artifacts[key]}")


if __name__ == "__main__":
    main()
