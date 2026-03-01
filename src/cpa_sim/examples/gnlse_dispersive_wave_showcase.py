from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

DEFAULT_OUT_DIR = Path("out")
DEFAULT_STAGE_NAME = "fiber_dispersive_wave"


def _plot_from_npz(
    *,
    npz_path: Path,
    wavelength_path: Path,
    delay_path: Path,
    center_wavelength_nm: float,
) -> None:
    data = np.load(npz_path)
    z_m = np.asarray(data["z_m"], dtype=float)
    t_fs = np.asarray(data["t_fs"], dtype=float)
    at = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(
        data["at_zt_imag"], dtype=float
    )

    delay_map = np.abs(at) ** 2

    fig, ax = plt.subplots(figsize=(8, 4.8))
    m = ax.pcolormesh(t_fs, z_m, np.log10(delay_map + 1e-12), shading="auto", cmap="magma")
    fig.colorbar(m, ax=ax, label="log10(|A(t,z)|²)")
    ax.set_xlabel("Delay (fs)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Delay vs distance")
    fig.tight_layout()
    fig.savefig(delay_path, dpi=170)
    plt.close(fig)

    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at, axes=1), axis=1), axes=1)
    spectrum_map = np.abs(aw) ** 2

    if "w_rad_per_fs" in data:
        w_rad_per_fs = np.asarray(data["w_rad_per_fs"], dtype=float)
    else:
        dt_s = float((t_fs[1] - t_fs[0]) * 1e-15)
        w_rad_per_fs = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t_fs.size, d=dt_s)) * 1e-15

    omega0_rad_per_s = 2.0 * np.pi * 299792458.0 / (center_wavelength_nm * 1e-9)
    omega_rad_per_s = omega0_rad_per_s + w_rad_per_fs * 1e15
    valid = omega_rad_per_s > 0.0
    wavelength_nm = np.full_like(omega_rad_per_s, np.nan, dtype=float)
    wavelength_nm[valid] = 2.0 * np.pi * 299792458.0 / omega_rad_per_s[valid] * 1e9

    fig, ax = plt.subplots(figsize=(8, 4.8))
    m = ax.pcolormesh(
        wavelength_nm,
        z_m,
        np.log10(spectrum_map + 1e-12),
        shading="auto",
        cmap="viridis",
    )
    fig.colorbar(m, ax=ax, label="log10(|A(ω,z)|²)")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Wavelength vs distance")
    fig.tight_layout()
    fig.savefig(wavelength_path, dpi=170)
    plt.close(fig)


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

    wavelength_img = stage_plot_dir / f"{DEFAULT_STAGE_NAME}_wavelength_vs_distance.png"
    delay_img = stage_plot_dir / f"{DEFAULT_STAGE_NAME}_delay_vs_distance.png"
    _plot_from_npz(
        npz_path=z_npz,
        wavelength_path=wavelength_img,
        delay_path=delay_img,
        center_wavelength_nm=835.0,
    )

    artifacts[f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance"] = str(wavelength_img)
    artifacts[f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance"] = str(delay_img)

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
        f"{DEFAULT_STAGE_NAME}.plot_wavelength_vs_distance",
        f"{DEFAULT_STAGE_NAME}.plot_delay_vs_distance",
    ):
        print(f"{key}: {artifacts[key]}")


if __name__ == "__main__":
    main()
