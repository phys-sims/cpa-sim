"""Dispersive-wave plotting helpers.

By default, heatmaps auto-zoom their x-axis to where signal exists (`xlim="auto"`).
Set `xlim=None` to force full-grid plotting, or pass `(xmin, xmax)` for manual limits.
"""

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
    xlim: str | tuple[float, float] | None = "auto",
    scale: str = "linear",
    axis_for_x: int = -1,
) -> None:
    if scale not in {"linear", "log"}:
        raise ValueError(f"Unsupported scale '{scale}'. Expected 'linear' or 'log'.")

    finite = values[np.isfinite(values)]
    if scale == "linear":
        vmin = 0.0
        vmax = float(np.nanpercentile(finite, 99.9)) if finite.size else 1.0
        if not np.isfinite(vmax) or vmax <= vmin:
            vmax = float(np.max(finite)) if finite.size else 1.0
        if not np.isfinite(vmax) or vmax <= vmin:
            vmax = 1.0
        norm = None
    else:
        colors = import_module("matplotlib.colors")
        positive = values[np.isfinite(values) & (values > 0.0)]
        if positive.size:
            vmin = float(np.nanpercentile(positive, 1.0))
            vmax = float(np.nanpercentile(positive, 99.9))
        else:
            vmin = 1e-12
            vmax = float(np.max(finite)) if finite.size else 1.0
        if not np.isfinite(vmin) or vmin <= 0.0:
            vmin = 1e-12
        if not np.isfinite(vmax) or vmax <= vmin:
            vmax = max(vmin * 10.0, 1e-11)
        norm = colors.LogNorm(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    mesh = ax.pcolormesh(
        x_axis,
        z_m,
        np.clip(values, vmin, vmax),
        shading="auto",
        cmap=cmap,
        vmin=None if norm is not None else vmin,
        vmax=None if norm is not None else vmax,
        norm=norm,
    )
    fig.colorbar(mesh, ax=ax, label=color_label)
    ax.set_xlabel(x_label)
    ax.set_ylabel("Distance (m)")
    ax.set_title(title)
    if xlim == "auto":
        ax.set_xlim(auto_xlim_from_intensity(x_axis, values, axis_for_x=axis_for_x))
    elif xlim is None:
        pass
    else:
        ax.set_xlim(xlim)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def auto_xlim_from_intensity(
    x: np.ndarray,
    I2d: np.ndarray,
    *,
    coverage: float = 0.999,
    pad_frac: float = 0.10,
    axis_for_x: int = -1,
) -> tuple[float, float]:
    """Estimate a robust x-axis window from 2D intensity support."""
    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim != 1 or x_arr.size == 0:
        raise ValueError("x must be a non-empty 1D array.")

    data = np.asarray(I2d, dtype=float)
    x_axis = axis_for_x if axis_for_x >= 0 else data.ndim + axis_for_x
    if x_axis < 0 or x_axis >= data.ndim:
        raise ValueError("axis_for_x is out of bounds for I2d.")
    if data.shape[x_axis] != x_arr.size:
        raise ValueError("I2d axis length for x does not match len(x).")

    reduce_axes = tuple(ax for ax in range(data.ndim) if ax != x_axis)
    clean_data = np.where(np.isfinite(data), np.clip(data, 0.0, None), 0.0)
    profile = np.max(clean_data, axis=reduce_axes) if reduce_axes else clean_data
    profile = np.asarray(profile, dtype=float)

    x_min = float(np.nanmin(x_arr))
    x_max = float(np.nanmax(x_arr))
    total = float(np.sum(profile))
    if not np.isfinite(total) or total <= 0.0:
        return x_min, x_max

    order = np.argsort(x_arr)
    x_sorted = x_arr[order]
    p_sorted = profile[order]
    total = float(np.sum(p_sorted))
    if total <= 0.0:
        return x_min, x_max

    cdf = np.cumsum(p_sorted) / total
    lo_q = (1.0 - coverage) / 2.0
    hi_q = 1.0 - lo_q
    lo = float(np.interp(lo_q, cdf, x_sorted))
    hi = float(np.interp(hi_q, cdf, x_sorted))

    if not np.isfinite(lo) or not np.isfinite(hi) or hi < lo:
        return x_min, x_max

    span = hi - lo
    if span <= 0.0:
        return x_min, x_max
    pad = pad_frac * span
    return lo - pad, hi + pad


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
        xlim=xlim,
        scale="linear",
    )
    _render_map(
        plt=plt,
        x_axis=t_fs,
        z_m=z_m,
        values=delay_power,
        cmap="magma",
        title="Delay vs distance (log)",
        x_label="Delay (fs)",
        color_label="|A(t,z)|²",
        out_path=paths.delay_log,
        xlim=xlim,
        scale="log",
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
        xlim=xlim,
        scale="linear",
    )
    _render_map(
        plt=plt,
        x_axis=wavelength_nm,
        z_m=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (log)",
        x_label="Wavelength (nm)",
        color_label="|A(ω,z)|²",
        out_path=paths.wavelength_log,
        xlim=xlim,
        scale="log",
    )
    return paths


def plot_dispersive_wave_maps_from_npz(
    *,
    npz_path: Path,
    center_wavelength_nm: float,
    out_dir: Path,
    stem: str,
    xlim: str | tuple[float, float] | None = "auto",
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
    )
