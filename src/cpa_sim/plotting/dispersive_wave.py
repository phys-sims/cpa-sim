from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

_LIGHT_SPEED_M_PER_S = 299792458.0


@dataclass(frozen=True)
class DispersiveWavePlotPaths:
    delay_linear: Path
    delay_log: Path
    wavelength_linear: Path
    wavelength_log: Path


def _load_pyplot() -> Any:
    matplotlib: Any = import_module("matplotlib")
    matplotlib.use("Agg")
    return import_module("matplotlib.pyplot")


def _wavelength_axis_nm(*, w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_s = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / (center_wavelength_nm * 1e-9)
    omega_rad_per_s = omega0_rad_per_s + w_rad_per_fs * 1e15

    wavelength_nm = np.full_like(omega_rad_per_s, np.nan, dtype=float)
    valid = omega_rad_per_s > 0.0
    wavelength_nm[valid] = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / omega_rad_per_s[valid] * 1e9
    return wavelength_nm


def _render_map(
    *,
    plt: Any,
    x_axis: np.ndarray,
    z_m: np.ndarray,
    values: np.ndarray,
    cmap: str,
    title: str,
    x_label: str,
    color_label: str,
    out_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    mesh = ax.pcolormesh(x_axis, z_m, values, shading="auto", cmap=cmap)
    fig.colorbar(mesh, ax=ax, label=color_label)
    ax.set_xlabel(x_label)
    ax.set_ylabel("Distance (m)")
    ax.set_title(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def build_default_plot_paths(*, out_dir: Path, stem: str) -> DispersiveWavePlotPaths:
    return DispersiveWavePlotPaths(
        delay_linear=out_dir / f"{stem}_delay_vs_distance_linear.png",
        delay_log=out_dir / f"{stem}_delay_vs_distance_log.png",
        wavelength_linear=out_dir / f"{stem}_wavelength_vs_distance_linear.png",
        wavelength_log=out_dir / f"{stem}_wavelength_vs_distance_log.png",
    )


def _resolve_w_rad_per_fs(*, t_fs: np.ndarray, w_rad_per_fs: np.ndarray | None) -> np.ndarray:
    if w_rad_per_fs is not None:
        return np.asarray(w_rad_per_fs, dtype=float)

    dt_s = float((t_fs[1] - t_fs[0]) * 1e-15)
    return np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t_fs.size, d=dt_s)) * 1e-15


def plot_dispersive_wave_maps(
    *,
    at_zt: np.ndarray,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    center_wavelength_nm: float,
    paths: DispersiveWavePlotPaths,
) -> DispersiveWavePlotPaths:
    """Generate delay/wavelength-vs-distance maps in linear and log scales."""
    plt = _load_pyplot()

    delay_power = np.abs(at_zt) ** 2
    _render_map(
        plt=plt,
        x_axis=t_fs,
        z_m=z_m,
        values=delay_power,
        cmap="magma",
        title="Delay vs distance (linear)",
        x_label="Delay (fs)",
        color_label="|A(t,z)|²",
        out_path=paths.delay_linear,
    )
    _render_map(
        plt=plt,
        x_axis=t_fs,
        z_m=z_m,
        values=np.log10(delay_power + 1e-12),
        cmap="magma",
        title="Delay vs distance (log10)",
        x_label="Delay (fs)",
        color_label="log10(|A(t,z)|²)",
        out_path=paths.delay_log,
    )

    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    spectrum_power = np.abs(aw) ** 2
    wavelength_nm = _wavelength_axis_nm(
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
    )

    _render_map(
        plt=plt,
        x_axis=wavelength_nm,
        z_m=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (linear)",
        x_label="Wavelength (nm)",
        color_label="|A(ω,z)|²",
        out_path=paths.wavelength_linear,
    )
    _render_map(
        plt=plt,
        x_axis=wavelength_nm,
        z_m=z_m,
        values=np.log10(spectrum_power + 1e-12),
        cmap="viridis",
        title="Wavelength vs distance (log10)",
        x_label="Wavelength (nm)",
        color_label="log10(|A(ω,z)|²)",
        out_path=paths.wavelength_log,
    )
    return paths


def plot_dispersive_wave_maps_from_npz(
    *,
    npz_path: Path,
    center_wavelength_nm: float,
    out_dir: Path,
    stem: str,
) -> DispersiveWavePlotPaths:
    """Load z-traces from a saved NPZ and emit standard dispersive-wave map artifacts."""
    data = np.load(npz_path)
    z_m = np.asarray(data["z_m"], dtype=float)
    t_fs = np.asarray(data["t_fs"], dtype=float)
    at_zt = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(
        data["at_zt_imag"], dtype=float
    )
    w_rad_per_fs = _resolve_w_rad_per_fs(
        t_fs=t_fs,
        w_rad_per_fs=np.asarray(data["w_rad_per_fs"], dtype=float)
        if "w_rad_per_fs" in data
        else None,
    )

    paths = build_default_plot_paths(out_dir=out_dir, stem=stem)
    return plot_dispersive_wave_maps(
        at_zt=at_zt,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        paths=paths,
    )
