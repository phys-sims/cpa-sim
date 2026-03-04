from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

_LIGHT_SPEED_M_PER_S = 299792458.0


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


def _render_map(*, x_axis: np.ndarray, z_m: np.ndarray, values: np.ndarray, cmap: str, title: str, x_label: str, color_label: str, out_path: Path) -> None:
    plt = _load_pyplot()
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


def plot_dispersive_wave_maps(
    *,
    at_zt: np.ndarray,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    center_wavelength_nm: float,
    delay_linear_path: Path,
    delay_log_path: Path,
    wavelength_linear_path: Path,
    wavelength_log_path: Path,
) -> None:
    """Generate delay/wavelength-vs-distance maps in linear and log scales."""
    delay_power = np.abs(at_zt) ** 2
    _render_map(
        x_axis=t_fs,
        z_m=z_m,
        values=delay_power,
        cmap="magma",
        title="Delay vs distance (linear)",
        x_label="Delay (fs)",
        color_label="|A(t,z)|²",
        out_path=delay_linear_path,
    )
    _render_map(
        x_axis=t_fs,
        z_m=z_m,
        values=np.log10(delay_power + 1e-12),
        cmap="magma",
        title="Delay vs distance (log10)",
        x_label="Delay (fs)",
        color_label="log10(|A(t,z)|²)",
        out_path=delay_log_path,
    )

    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    spectrum_power = np.abs(aw) ** 2
    wavelength_nm = _wavelength_axis_nm(
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
    )

    _render_map(
        x_axis=wavelength_nm,
        z_m=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (linear)",
        x_label="Wavelength (nm)",
        color_label="|A(ω,z)|²",
        out_path=wavelength_linear_path,
    )
    _render_map(
        x_axis=wavelength_nm,
        z_m=z_m,
        values=np.log10(spectrum_power + 1e-12),
        cmap="viridis",
        title="Wavelength vs distance (log10)",
        x_label="Wavelength (nm)",
        color_label="log10(|A(ω,z)|²)",
        out_path=wavelength_log_path,
    )
