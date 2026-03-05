"""Dispersive-wave plotting helpers.

By default, heatmaps auto-zoom their x-axis to where signal exists (`xlim="auto"`).
Set `xlim=None` to force full-grid plotting, or pass `(xmin, xmax)` for manual limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .common import plot_heatmap

_LIGHT_SPEED_M_PER_S = 299792458.0


@dataclass(frozen=True)
class DispersiveWavePlotPaths:
    delay_linear: Path
    delay_log: Path
    wavelength_linear: Path
    wavelength_log: Path


def _wavelength_axis_nm(*, w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_s = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / (center_wavelength_nm * 1e-9)
    omega_rad_per_s = omega0_rad_per_s + w_rad_per_fs * 1e15

    wavelength_nm = np.full_like(omega_rad_per_s, np.nan, dtype=float)
    valid = omega_rad_per_s > 0.0
    wavelength_nm[valid] = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / omega_rad_per_s[valid] * 1e9
    return wavelength_nm


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
    xlim: str | tuple[float, float] | None = "auto",
    linear_percentile: float = 99.9,
    log_vmax_percentile: float | None = 99.9,
    log_dynamic_range_db: float = 60.0,
) -> DispersiveWavePlotPaths:
    """Generate delay/wavelength-vs-distance maps in linear and log scales."""
    delay_power = np.abs(at_zt) ** 2
    plot_heatmap(
        out_path=paths.delay_linear,
        x_axis=t_fs,
        y_axis=z_m,
        values=delay_power,
        cmap="magma",
        title="Delay vs distance (linear)",
        x_label="Delay (fs)",
        y_label="Distance (m)",
        color_label="|A(t,z)|²",
        xlim=xlim,
        scale="linear",
        linear_percentile=linear_percentile,
    )
    plot_heatmap(
        out_path=paths.delay_log,
        x_axis=t_fs,
        y_axis=z_m,
        values=delay_power,
        cmap="magma",
        title="Delay vs distance (log)",
        x_label="Delay (fs)",
        y_label="Distance (m)",
        color_label="|A(t,z)|²",
        xlim=xlim,
        scale="log",
        log_vmax_percentile=log_vmax_percentile,
        log_dynamic_range_db=log_dynamic_range_db,
    )

    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    spectrum_power = np.abs(aw) ** 2
    wavelength_nm = _wavelength_axis_nm(
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
    )

    # The ω→λ mapping produces NaNs for invalid (ω<=0) bins. Those bins are unphysical
    # in wavelength space and they also break "auto" x-limits (CDF interpolation).
    # Filter them out, then sort wavelength so the x-axis is strictly increasing.
    finite = np.isfinite(wavelength_nm)
    if np.any(finite):
        wavelength_nm = wavelength_nm[finite]
        spectrum_power = spectrum_power[:, finite]
        order = np.argsort(wavelength_nm)
        wavelength_nm = wavelength_nm[order]
        spectrum_power = spectrum_power[:, order]

    plot_heatmap(
        out_path=paths.wavelength_linear,
        x_axis=wavelength_nm,
        y_axis=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (linear)",
        x_label="Wavelength (nm)",
        y_label="Distance (m)",
        color_label="|A(ω,z)|²",
        xlim=xlim,
        scale="linear",
        linear_percentile=linear_percentile,
    )
    plot_heatmap(
        out_path=paths.wavelength_log,
        x_axis=wavelength_nm,
        y_axis=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (log)",
        x_label="Wavelength (nm)",
        y_label="Distance (m)",
        color_label="|A(ω,z)|²",
        xlim=xlim,
        scale="log",
        log_vmax_percentile=log_vmax_percentile,
        log_dynamic_range_db=log_dynamic_range_db,
    )
    return paths


def plot_dispersive_wave_maps_from_npz(
    *,
    npz_path: Path,
    center_wavelength_nm: float,
    out_dir: Path,
    stem: str,
    xlim: str | tuple[float, float] | None = "auto",
    linear_percentile: float = 99.9,
    log_vmax_percentile: float | None = 99.9,
    log_dynamic_range_db: float = 60.0,
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
        xlim=xlim,
        linear_percentile=linear_percentile,
        log_vmax_percentile=log_vmax_percentile,
        log_dynamic_range_db=log_dynamic_range_db,
    )
