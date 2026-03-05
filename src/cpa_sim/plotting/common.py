from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class LineSeries:
    x: np.ndarray
    y: np.ndarray
    label: str


def load_pyplot() -> Any:
    matplotlib: Any = import_module("matplotlib")
    matplotlib.use("Agg")
    return import_module("matplotlib.pyplot")


def autoscale_window_1d(
    *, x_axis: np.ndarray, values: np.ndarray, threshold_fraction: float = 1e-3
) -> tuple[float, float] | None:
    if x_axis.size == 0 or values.size == 0:
        return None

    x = np.asarray(x_axis, dtype=float)
    y = np.asarray(values, dtype=float)

    finite = np.isfinite(x) & np.isfinite(y)
    if not np.any(finite):
        return None

    x = x[finite]
    y = np.abs(y[finite])
    peak = float(np.max(y))
    if peak <= 0.0:
        return (float(np.min(x)), float(np.max(x)))

    support = np.where(y >= peak * threshold_fraction)[0]
    if support.size == 0:
        return (float(np.min(x)), float(np.max(x)))

    lo = float(np.min(x[support]))
    hi = float(np.max(x[support]))
    if np.isclose(lo, hi):
        span = float(np.max(x) - np.min(x))
        pad = 0.05 * span if span > 0.0 else 1.0
        return (lo - pad, hi + pad)

    pad = 0.05 * (hi - lo)
    return (lo - pad, hi + pad)


def auto_xlim_from_intensity(
    x: np.ndarray,
    intensity_2d: np.ndarray,
    *,
    coverage: float = 0.999,
    pad_frac: float = 0.10,
    axis_for_x: int = -1,
) -> tuple[float, float]:
    """Estimate a robust x-axis window from 2D intensity support."""
    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim != 1 or x_arr.size == 0:
        raise ValueError("x must be a non-empty 1D array.")

    data = np.asarray(intensity_2d, dtype=float)
    x_axis = axis_for_x if axis_for_x >= 0 else data.ndim + axis_for_x
    if x_axis < 0 or x_axis >= data.ndim:
        raise ValueError("axis_for_x is out of bounds for intensity_2d.")
    if data.shape[x_axis] != x_arr.size:
        raise ValueError("intensity_2d axis length for x does not match len(x).")

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


def plot_line_series(
    *,
    out_path: Path,
    series: Sequence[LineSeries],
    x_label: str,
    y_label: str,
    title: str,
    figsize: tuple[float, float] = (8, 4.5),
    plot_format: str | None = None,
    auto_xlim: bool = False,
) -> Path:
    plt = load_pyplot()

    fig, ax = plt.subplots(figsize=figsize)
    for entry in series:
        x = np.asarray(entry.x, dtype=float)
        y = np.asarray(entry.y, dtype=float)
        ax.plot(x, y, label=entry.label)

    if auto_xlim and series:
        xlim = autoscale_window_1d(
            x_axis=np.asarray(series[0].x, dtype=float), values=np.asarray(series[0].y, dtype=float)
        )
        if xlim is not None:
            ax.set_xlim(*xlim)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    if any(entry.label for entry in series):
        ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if plot_format is None:
        fig.savefig(out_path)
    else:
        fig.savefig(out_path, format=plot_format)
    plt.close(fig)
    return out_path


def plot_heatmap(
    *,
    out_path: Path,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    values: np.ndarray,
    cmap: str,
    title: str,
    x_label: str,
    y_label: str,
    color_label: str,
    scale: str,
    xlim: str | tuple[float, float] | None = "auto",
    axis_for_x: int = -1,
    figsize: tuple[float, float] = (8, 4.8),
) -> Path:
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

    plt = load_pyplot()
    fig, ax = plt.subplots(figsize=figsize)
    mesh = ax.pcolormesh(
        x_axis,
        y_axis,
        np.clip(values, vmin, vmax),
        shading="auto",
        cmap=cmap,
        vmin=None if norm is not None else vmin,
        vmax=None if norm is not None else vmax,
        norm=norm,
    )
    fig.colorbar(mesh, ax=ax, label=color_label)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    if xlim == "auto":
        ax.set_xlim(auto_xlim_from_intensity(x_axis, values, axis_for_x=axis_for_x))
    elif xlim is not None:
        ax.set_xlim(xlim)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    return out_path
