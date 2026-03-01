"""Reproduce dispersive-wave emission in anomalous-regime fiber propagation.

This script demonstrates supercontinuum dynamics where a femtosecond pulse launched in
anomalous dispersion emits a short-wavelength dispersive wave under higher-order
phase matching. The most important knobs are:

- higher-order dispersion (Taylor beta coefficients),
- Raman response model selection, and
- self-steepening (optical shock term).

The setup is aligned with the `gnlse-python` dispersive-wave / Raman examples
(`example_dispersive_wave`, `test_raman`) but executed through cpa-sim's stage/config
API so it can be used as a reproducible, user-facing workflow.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

_LIGHT_SPEED_M_PER_S = 299_792_458.0
_EPS = 1e-30
_STAGE_NAME = "fiber_dispersive_wave"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate dispersive-wave figures with cpa-sim + WUST gnlse"
    )
    parser.add_argument(
        "--outdir", type=Path, required=True, help="Output directory for generated figures"
    )
    parser.add_argument(
        "--n-samples", type=int, default=8192, help="Pulse temporal grid sample count"
    )
    parser.add_argument(
        "--z-saves", type=int, default=400, help="Number of saved z-slices from gnlse"
    )
    parser.add_argument(
        "--raman-model",
        type=str,
        default="blowwood",
        choices=["blowwood", "linagrawal", "hollenbeck", "none"],
        help="Raman response model (or 'none' to disable Raman)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Quick mode: overrides to n_samples=4096 and z_saves=150",
    )
    return parser


def _to_wavelength_nm(w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_s = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / (center_wavelength_nm * 1e-9)
    omega_abs_rad_per_s = omega0_rad_per_s + (w_rad_per_fs * 1e15)

    lam_nm = np.full_like(omega_abs_rad_per_s, np.nan, dtype=float)
    valid = omega_abs_rad_per_s > 0.0
    lam_nm[valid] = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / omega_abs_rad_per_s[valid] * 1e9
    return lam_nm


def _load_z_traces(npz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(npz_path)
    z_m = np.asarray(data["z_m"], dtype=float)
    t_fs = np.asarray(data["t_fs"], dtype=float)
    w_rad_per_fs = np.asarray(data["w_rad_per_fs"], dtype=float)
    at = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(
        data["at_zt_imag"], dtype=float
    )
    return z_m, t_fs, w_rad_per_fs, at


def _save_plots(
    *,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    at_zt: np.ndarray,
    center_wavelength_nm: float,
    outdir: Path,
) -> dict[str, Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    wavelength_nm = _to_wavelength_nm(w_rad_per_fs, center_wavelength_nm=center_wavelength_nm)
    aw_zt = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)

    power_t = np.abs(at_zt) ** 2
    power_w = np.abs(aw_zt) ** 2

    spectrum_path = outdir / "spectrum_z0_vs_zL.png"
    wavelength_path = outdir / "evolution_wavelength_vs_distance.png"
    delay_path = outdir / "evolution_delay_vs_distance.png"

    matplotlib.rcParams.update(
        {
            "figure.dpi": 170,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "font.size": 11,
        }
    )

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(wavelength_nm, np.log10(power_w[0] + _EPS), label="z = 0")
    ax.plot(wavelength_nm, np.log10(power_w[-1] + _EPS), label=f"z = {z_m[-1]:.3f} m")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel(r"$\log_{10}(P_\lambda)$ [a.u.]")
    ax.set_title("Dispersive-wave spectrum evolution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(spectrum_path)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    m = ax.pcolormesh(wavelength_nm, z_m, np.log10(power_w + _EPS), shading="auto", cmap="viridis")
    fig.colorbar(m, ax=ax, label=r"$\log_{10}(P_\lambda)$ [a.u.]")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Wavelength vs distance")
    fig.tight_layout()
    fig.savefig(wavelength_path)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    m = ax.pcolormesh(t_fs, z_m, np.log10(power_t + _EPS), shading="auto", cmap="magma")
    fig.colorbar(m, ax=ax, label=r"$\log_{10}(|A(t,z)|^2)$ [a.u.]")
    ax.set_xlabel("Delay (fs)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Delay vs distance")
    fig.tight_layout()
    fig.savefig(delay_path)
    plt.close(fig)

    return {
        "spectrum_comparison": spectrum_path,
        "wavelength_evolution": wavelength_path,
        "delay_evolution": delay_path,
    }


def main() -> None:
    args = _build_parser().parse_args()
    outdir = args.outdir

    n_samples = 4096 if args.fast else args.n_samples
    z_saves = 150 if args.fast else args.z_saves

    raman_cfg = None if args.raman_model == "none" else RamanCfg(model=args.raman_model)

    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=7),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    center_wavelength_nm=835.0,
                    shape="sech2",
                    width_fs=50.284,
                    peak_power_w=10000.0,
                    n_samples=n_samples,
                    time_window_fs=12500.0,
                )
            )
        ),
        stages=[
            FiberCfg(
                name=_STAGE_NAME,
                physics=FiberPhysicsCfg(
                    length_m=0.15,
                    loss_db_per_m=0.0,
                    gamma_1_per_w_m=0.11,
                    self_steepening=True,
                    dispersion=DispersionTaylorCfg(
                        betas_psn_per_m=[
                            -11.830e-3,
                            8.1038e-5,
                            -9.5205e-8,
                            2.0737e-10,
                            -5.3943e-13,
                            1.3486e-15,
                            -2.5495e-18,
                            3.0524e-21,
                            -1.7140e-24,
                        ]
                    ),
                    raman=raman_cfg,
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=z_saves,
                    keep_full_solution=True,
                ),
            )
        ],
    )

    result = run_pipeline(
        cfg,
        policy={
            "cpa.emit_stage_plots": True,
            "cpa.stage_plot_dir": str(outdir),
        },
    )

    artifacts = {**result.artifacts, **result.state.artifacts}
    z_traces_npz = Path(artifacts[f"{_STAGE_NAME}.z_traces_npz"])

    z_m, t_fs, w_rad_per_fs, at_zt = _load_z_traces(z_traces_npz)
    fig_paths = _save_plots(
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        at_zt=at_zt,
        center_wavelength_nm=835.0,
        outdir=outdir,
    )

    print("Generated dispersive-wave artifacts:")
    print(f"  z-traces npz       : {z_traces_npz}")
    print(f"  spectrum z0 vs zL  : {fig_paths['spectrum_comparison']}")
    print(f"  wavelength vs z    : {fig_paths['wavelength_evolution']}")
    print(f"  delay vs z         : {fig_paths['delay_evolution']}")


if __name__ == "__main__":
    main()
