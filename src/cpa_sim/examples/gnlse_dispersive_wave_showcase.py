from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from cpa_sim.models import (
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
from cpa_sim.pipeline import run_pipeline
from cpa_sim.plotting import plot_dispersive_wave_maps

DEFAULT_OUT_DIR = Path("out")
DEFAULT_STAGE_NAME = "fiber_dispersive_wave"


def _plot_from_npz(
    *,
    npz_path: Path,
    wavelength_linear_path: Path,
    wavelength_log_path: Path,
    delay_linear_path: Path,
    delay_log_path: Path,
    center_wavelength_nm: float,
) -> None:
    data = np.load(npz_path)
    z_m = np.asarray(data["z_m"], dtype=float)
    t_fs = np.asarray(data["t_fs"], dtype=float)
    at = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(
        data["at_zt_imag"], dtype=float
    )

    if "w_rad_per_fs" in data:
        w_rad_per_fs = np.asarray(data["w_rad_per_fs"], dtype=float)
    else:
        dt_s = float((t_fs[1] - t_fs[0]) * 1e-15)
        w_rad_per_fs = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t_fs.size, d=dt_s)) * 1e-15

    plot_dispersive_wave_maps(
        at_zt=at,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        delay_linear_path=delay_linear_path,
        delay_log_path=delay_log_path,
        wavelength_linear_path=wavelength_linear_path,
        wavelength_log_path=wavelength_log_path,
    )


def run_showcase(*, out_dir: Path, seed: int = 7) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_plot_dir = out_dir / "stage_plots"

    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    amplitude=40.0,
                    width_fs=50.0,
                    center_wavelength_nm=835.0,
                    n_samples=2048,
                    time_window_fs=12000.0,
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
                    dispersion=DispersionTaylorCfg(betas_psn_per_m=[-0.011830, 0.000084]),
                    raman=RamanCfg(model="blowwood"),
                    self_steepening=True,
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=200,
                    keep_full_solution=True,
                ),
            )
        ],
    )

    result = run_pipeline(
        cfg,
        policy={
            "cpa.emit_stage_plots": True,
            "cpa.stage_plot_dir": str(stage_plot_dir),
        },
    )

    artifacts = {**result.artifacts, **result.state.artifacts}
    z_npz = Path(artifacts[f"{DEFAULT_STAGE_NAME}.z_traces_npz"])

    wavelength_linear_img = (
        stage_plot_dir / f"{DEFAULT_STAGE_NAME}_wavelength_vs_distance_linear.png"
    )
    wavelength_log_img = stage_plot_dir / f"{DEFAULT_STAGE_NAME}_wavelength_vs_distance_log.png"
    delay_linear_img = stage_plot_dir / f"{DEFAULT_STAGE_NAME}_delay_vs_distance_linear.png"
    delay_log_img = stage_plot_dir / f"{DEFAULT_STAGE_NAME}_delay_vs_distance_log.png"
    _plot_from_npz(
        npz_path=z_npz,
        wavelength_linear_path=wavelength_linear_img,
        wavelength_log_path=wavelength_log_img,
        delay_linear_path=delay_linear_img,
        delay_log_path=delay_log_img,
        center_wavelength_nm=835.0,
    )

    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_linear"] = str(
        wavelength_linear_img
    )
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance_log"] = str(wavelength_log_img)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_linear"] = str(delay_linear_img)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance_log"] = str(delay_log_img)

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
