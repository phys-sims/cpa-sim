"""Dispersive-wave plotting helpers.

By default, heatmaps auto-zoom their x-axis to where signal exists (`xlim="auto"`).
Set `xlim=None` to force full-grid plotting, or pass `(xmin, xmax)` for manual limits.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from cpa_sim.models.plotting_policy import HeatmapNormPolicy, PlotWindowPolicy

from .common import load_pyplot, plot_heatmap

_LIGHT_SPEED_M_PER_S = 299792458.0
_FS_TO_PS = 1e-3
_WUST_LOG_FLOOR_DB = -40.0
_WUST_DEFAULT_TIME_RANGE_PS = (-0.5, 5.0)
_WUST_DEFAULT_WL_RANGE_NM = (400.0, 1400.0)


@dataclass(frozen=True)
class DispersiveWavePlotPaths:
    delay_linear: Path
    delay_log: Path
    wavelength_linear: Path
    wavelength_log: Path


@dataclass(frozen=True)
class _WustMapData:
    z_m: np.ndarray
    delay_ps: np.ndarray
    delay_linear: np.ndarray
    delay_log_db: np.ndarray
    wavelength_nm: np.ndarray
    wavelength_linear: np.ndarray
    wavelength_log_db: np.ndarray
    time_range_ps: tuple[float, float]
    wl_range_nm: tuple[float, float]
    aw_source: Literal["saved_aw", "fft_at"]


def _dispersive_wave_default_policy(plot_policy: PlotWindowPolicy | None) -> PlotWindowPolicy:
    if plot_policy is None:
        return PlotWindowPolicy(
            heatmap_norm=HeatmapNormPolicy(
                scale="log",
                vmin_percentile=0.05,
                vmax_percentile=99.95,
                dynamic_range_db=45.0,
                gamma=0.85,
            )
        )

    return PlotWindowPolicy(
        line=plot_policy.line,
        heatmap=plot_policy.heatmap,
        heatmap_norm=HeatmapNormPolicy(
            scale=plot_policy.heatmap_norm.scale,
            vmin_percentile=plot_policy.heatmap_norm.vmin_percentile,
            vmax_percentile=plot_policy.heatmap_norm.vmax_percentile,
            dynamic_range_db=plot_policy.heatmap_norm.dynamic_range_db,
            gamma=plot_policy.heatmap_norm.gamma,
        ),
    )


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

    if t_fs.size < 2:
        raise ValueError("t_fs must include at least two points when w_rad_per_fs is missing.")
    dt_s = float((t_fs[1] - t_fs[0]) * 1e-15)
    return np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t_fs.size, d=dt_s)) * 1e-15


def _normalize_by_max(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return np.zeros_like(array, dtype=float)

    domain_max = float(np.max(finite))
    if domain_max <= 0.0:
        return np.zeros_like(array, dtype=float)

    normalized = np.where(np.isfinite(array), array / domain_max, 0.0)
    return np.clip(normalized, 0.0, None)


def _to_db_floor(values: np.ndarray, *, floor_db: float = _WUST_LOG_FLOOR_DB) -> np.ndarray:
    safe = np.maximum(np.asarray(values, dtype=float), np.finfo(float).tiny)
    values_db = 10.0 * np.log10(safe)
    return np.maximum(values_db, floor_db)


def _resolve_range_or_default(
    range_values: Sequence[float] | None,
    *,
    default: tuple[float, float],
    name: str,
) -> tuple[float, float]:
    if range_values is None:
        return default
    if len(range_values) != 2:
        raise ValueError(f"{name} must contain exactly two values.")
    start = float(range_values[0])
    stop = float(range_values[1])
    if not np.isfinite(start) or not np.isfinite(stop):
        raise ValueError(f"{name} values must be finite.")
    return (min(start, stop), max(start, stop))


def _resolve_aw_zw(*, at_zt: np.ndarray, aw_zw: np.ndarray | None) -> tuple[np.ndarray, str]:
    if aw_zw is not None:
        return np.asarray(aw_zw, dtype=np.complex128), "saved_aw"
    computed = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    return computed, "fft_at"


def _crop_wavelength_range(
    *,
    wavelength_nm: np.ndarray,
    values: np.ndarray,
    wl_range_nm: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    in_range = (wavelength_nm >= wl_range_nm[0]) & (wavelength_nm <= wl_range_nm[1])
    if np.count_nonzero(in_range) < 2:
        raise ValueError(f"wl_range_nm={wl_range_nm} includes fewer than two wavelength samples.")
    return wavelength_nm[in_range], values[:, in_range]


def _interpolate_to_uniform_wavelength_grid(
    *,
    wavelength_nm: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if wavelength_nm.size < 2:
        raise ValueError("At least two wavelength samples are required for interpolation.")

    wl_uniform = np.linspace(float(wavelength_nm[0]), float(wavelength_nm[-1]), wavelength_nm.size)
    out_values = np.empty((values.shape[0], wl_uniform.size), dtype=float)

    # Upstream code used scipy.interp2d, now deprecated. We only need wavelength-axis
    # interpolation (same Z samples in/out), so row-wise linear interpolation is equivalent.
    for row_idx in range(values.shape[0]):
        row = values[row_idx]
        out_values[row_idx] = np.interp(
            wl_uniform,
            wavelength_nm,
            row,
            left=float(row[0]),
            right=float(row[-1]),
        )
    return wl_uniform, out_values


def _load_npz_traces(
    *,
    npz_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    with np.load(npz_path) as data:
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
        if "aw_zw_real" in data and "aw_zw_imag" in data:
            aw_zw = np.asarray(data["aw_zw_real"], dtype=float) + 1j * np.asarray(
                data["aw_zw_imag"], dtype=float
            )
        else:
            aw_zw = None
    return z_m, t_fs, w_rad_per_fs, at_zt, aw_zw


def _prepare_wust_map_data(
    *,
    at_zt: np.ndarray,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    center_wavelength_nm: float,
    aw_zw: np.ndarray | None,
    time_range_ps: Sequence[float] | None,
    wl_range_nm: Sequence[float] | None,
) -> _WustMapData:
    at_zt_array = np.asarray(at_zt, dtype=np.complex128)
    if at_zt_array.ndim != 2:
        raise ValueError("at_zt must be a 2D array with shape (n_z, n_t).")

    z_axis = np.asarray(z_m, dtype=float)
    t_axis_fs = np.asarray(t_fs, dtype=float)
    w_axis = np.asarray(w_rad_per_fs, dtype=float)
    if at_zt_array.shape != (z_axis.size, t_axis_fs.size):
        raise ValueError("at_zt shape must be (len(z_m), len(t_fs)).")
    if w_axis.size != t_axis_fs.size:
        raise ValueError("w_rad_per_fs length must match len(t_fs).")

    resolved_time_range = _resolve_range_or_default(
        time_range_ps,
        default=_WUST_DEFAULT_TIME_RANGE_PS,
        name="time_range_ps",
    )
    resolved_wl_range = _resolve_range_or_default(
        wl_range_nm,
        default=_WUST_DEFAULT_WL_RANGE_NM,
        name="wl_range_nm",
    )

    delay_ps = t_axis_fs * _FS_TO_PS
    delay_linear = _normalize_by_max(np.abs(at_zt_array) ** 2)
    delay_log_db = _to_db_floor(delay_linear)

    aw_matrix, aw_source = _resolve_aw_zw(at_zt=at_zt_array, aw_zw=aw_zw)
    if aw_matrix.shape != at_zt_array.shape:
        raise ValueError("AW trace shape must match At trace shape.")
    spectrum_linear = _normalize_by_max(np.abs(aw_matrix) ** 2)

    wavelength_nm = _wavelength_axis_nm(
        w_rad_per_fs=w_axis,
        center_wavelength_nm=center_wavelength_nm,
    )
    finite = np.isfinite(wavelength_nm)
    if np.count_nonzero(finite) < 2:
        raise ValueError("Wavelength conversion produced fewer than two finite samples.")

    wavelength_finite = wavelength_nm[finite]
    spectrum_finite = spectrum_linear[:, finite]

    order = np.argsort(wavelength_finite)
    wavelength_sorted = wavelength_finite[order]
    spectrum_sorted = spectrum_finite[:, order]

    wavelength_cropped, spectrum_cropped = _crop_wavelength_range(
        wavelength_nm=wavelength_sorted,
        values=spectrum_sorted,
        wl_range_nm=resolved_wl_range,
    )
    wl_uniform, spectrum_uniform = _interpolate_to_uniform_wavelength_grid(
        wavelength_nm=wavelength_cropped,
        values=spectrum_cropped,
    )

    aw_source_literal: Literal["saved_aw", "fft_at"] = (
        "saved_aw" if aw_source == "saved_aw" else "fft_at"
    )

    return _WustMapData(
        z_m=z_axis,
        delay_ps=delay_ps,
        delay_linear=delay_linear,
        delay_log_db=delay_log_db,
        wavelength_nm=wl_uniform,
        wavelength_linear=spectrum_uniform,
        wavelength_log_db=_to_db_floor(spectrum_uniform),
        time_range_ps=resolved_time_range,
        wl_range_nm=resolved_wl_range,
        aw_source=aw_source_literal,
    )


def _render_wust_delay_map(
    *, ax: Any, map_data: _WustMapData, scale: Literal["linear", "log"]
) -> Any:
    values = map_data.delay_linear if scale == "linear" else map_data.delay_log_db
    artist = ax.pcolormesh(
        map_data.delay_ps,
        map_data.z_m,
        values,
        shading="auto",
        cmap="magma",
        vmin=0.0 if scale == "linear" else _WUST_LOG_FLOOR_DB,
    )
    ax.set_xlim(map_data.time_range_ps)
    ax.set_xlabel("Delay [ps]")
    ax.set_ylabel("Distance [m]")
    return artist


def _render_wust_wavelength_map(
    *, ax: Any, map_data: _WustMapData, scale: Literal["linear", "log"]
) -> Any:
    values = map_data.wavelength_linear if scale == "linear" else map_data.wavelength_log_db
    artist = ax.imshow(
        values,
        origin="lower",
        aspect="auto",
        cmap="magma",
        extent=[
            float(np.min(map_data.wavelength_nm)),
            float(np.max(map_data.wavelength_nm)),
            float(np.min(map_data.z_m)),
            float(np.max(map_data.z_m)),
        ],
        vmin=0.0 if scale == "linear" else _WUST_LOG_FLOOR_DB,
    )
    ax.set_xlim(map_data.wl_range_nm)
    ax.set_xlabel("Wavelength [nm]")
    ax.set_ylabel("Distance [m]")
    return artist


def _save_wust_map(
    *,
    out_path: Path,
    renderer: Any,
) -> None:
    plt = load_pyplot()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    artist = renderer(ax)
    fig.colorbar(artist, ax=ax)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def _plot_wust_maps(
    *, paths: DispersiveWavePlotPaths, map_data: _WustMapData
) -> DispersiveWavePlotPaths:
    _save_wust_map(
        out_path=paths.delay_linear,
        renderer=lambda ax: _render_wust_delay_map(ax=ax, map_data=map_data, scale="linear"),
    )
    _save_wust_map(
        out_path=paths.delay_log,
        renderer=lambda ax: _render_wust_delay_map(ax=ax, map_data=map_data, scale="log"),
    )
    _save_wust_map(
        out_path=paths.wavelength_linear,
        renderer=lambda ax: _render_wust_wavelength_map(ax=ax, map_data=map_data, scale="linear"),
    )
    _save_wust_map(
        out_path=paths.wavelength_log,
        renderer=lambda ax: _render_wust_wavelength_map(ax=ax, map_data=map_data, scale="log"),
    )
    return paths


def plot_dispersive_wave_maps(
    *,
    at_zt: np.ndarray,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    center_wavelength_nm: float,
    paths: DispersiveWavePlotPaths,
    xlim: str | tuple[float, float] | None = "auto",
    plot_policy: PlotWindowPolicy | None = None,
    compat_mode: Literal["default", "wust"] = "default",
    time_range_ps: Sequence[float] | None = None,
    wl_range_nm: Sequence[float] | None = None,
    aw_zw: np.ndarray | None = None,
) -> DispersiveWavePlotPaths:
    """Generate delay/wavelength-vs-distance maps in linear and log scales."""
    if compat_mode not in {"default", "wust"}:
        raise ValueError("compat_mode must be 'default' or 'wust'.")

    if compat_mode == "wust":
        wust_data = _prepare_wust_map_data(
            at_zt=at_zt,
            z_m=z_m,
            t_fs=t_fs,
            w_rad_per_fs=w_rad_per_fs,
            center_wavelength_nm=center_wavelength_nm,
            aw_zw=aw_zw,
            time_range_ps=time_range_ps,
            wl_range_nm=wl_range_nm,
        )
        return _plot_wust_maps(paths=paths, map_data=wust_data)

    effective_policy = _dispersive_wave_default_policy(plot_policy)

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
        color_label="|A(t,z)|^2",
        xlim=xlim,
        scale="linear",
        plot_policy=effective_policy,
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
        color_label="|A(t,z)|^2",
        xlim=xlim,
        scale="log",
        plot_policy=effective_policy,
    )

    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    spectrum_power = np.abs(aw) ** 2
    wavelength_nm = _wavelength_axis_nm(
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
    )

    plot_heatmap(
        out_path=paths.wavelength_linear,
        x_axis=wavelength_nm,
        y_axis=z_m,
        values=spectrum_power,
        cmap="viridis",
        title="Wavelength vs distance (linear)",
        x_label="Wavelength (nm)",
        y_label="Distance (m)",
        color_label="|A(w,z)|^2",
        xlim=xlim,
        scale="linear",
        plot_policy=effective_policy,
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
        color_label="|A(w,z)|^2",
        xlim=xlim,
        scale="log",
        plot_policy=effective_policy,
    )
    return paths


def plot_dispersive_wave_maps_from_npz(
    *,
    npz_path: Path,
    center_wavelength_nm: float,
    out_dir: Path,
    stem: str,
    xlim: str | tuple[float, float] | None = "auto",
    plot_policy: PlotWindowPolicy | None = None,
    compat_mode: Literal["default", "wust"] = "default",
    time_range_ps: Sequence[float] | None = None,
    wl_range_nm: Sequence[float] | None = None,
) -> DispersiveWavePlotPaths:
    """Load z-traces from a saved NPZ and emit dispersive-wave map artifacts."""
    z_m, t_fs, w_rad_per_fs, at_zt, aw_zw = _load_npz_traces(npz_path=npz_path)
    paths = build_default_plot_paths(out_dir=out_dir, stem=stem)
    return plot_dispersive_wave_maps(
        at_zt=at_zt,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        paths=paths,
        xlim=xlim,
        plot_policy=plot_policy,
        compat_mode=compat_mode,
        time_range_ps=time_range_ps,
        wl_range_nm=wl_range_nm,
        aw_zw=aw_zw,
    )
