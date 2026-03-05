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

    # If the x-axis contains non-finite entries (e.g. NaNs from invalid ω→λ conversion),
    # drop those bins so they don't poison the CDF-based window estimate.
    finite_x = np.isfinite(x_arr)
    if not np.all(finite_x):
        idx = np.where(finite_x)[0]
        if idx.size == 0:
            x_min = float(np.nanmin(x_arr))
            x_max = float(np.nanmax(x_arr))
            return x_min, x_max
        x_arr = x_arr[idx]
        data = np.take(data, idx, axis=x_axis)

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
    vmin: float | None = None,
    vmax: float | None = None,
    linear_percentile: float = 99.9,
    log_vmax_percentile: float | None = 99.9,
    log_dynamic_range_db: float = 60.0,
    clip_data: bool = False,
) -> Path:
    """Plot a 2D heatmap.

    The default normalization is chosen to be stable for GNLS/SSFM style evolution maps:

    - ``scale='linear'``: ``vmin=0`` and ``vmax`` is the ``linear_percentile`` percentile.
    - ``scale='log'``: ``vmax`` is the ``log_vmax_percentile`` percentile of positive values
      (or the max if ``log_vmax_percentile=None``) and ``vmin`` is set from a fixed dynamic
      range in dB relative to that peak:

        ``vmin = vmax / 10**(log_dynamic_range_db/10)``.

      This mimics the common "show N dB below peak" convention used in many WUST/GNLSE
      example figures and avoids percentile-based vmin choices that can hide weak features.

    You can override auto-scaling by explicitly passing ``vmin`` and/or ``vmax``.
    """

    if scale not in {"linear", "log"}:
        raise ValueError(f"Unsupported scale '{scale}'. Expected 'linear' or 'log'.")

    data = np.asarray(values, dtype=float)
    finite = data[np.isfinite(data)]

    norm = None
    vmin_plot: float
    vmax_plot: float

    if scale == "linear":
        vmin_plot = float(vmin) if vmin is not None else 0.0
        if vmax is not None:
            vmax_plot = float(vmax)
        else:
            vmax_plot = float(np.nanpercentile(finite, linear_percentile)) if finite.size else 1.0
        if not np.isfinite(vmax_plot) or vmax_plot <= vmin_plot:
            vmax_plot = float(np.nanmax(finite)) if finite.size else (vmin_plot + 1.0)
        if not np.isfinite(vmax_plot) or vmax_plot <= vmin_plot:
            vmax_plot = vmin_plot + 1.0
    else:
        colors = import_module("matplotlib.colors")
        positive = data[np.isfinite(data) & (data > 0.0)]

        if vmax is not None:
            vmax_plot = float(vmax)
        elif positive.size:
            if log_vmax_percentile is None:
                vmax_plot = float(np.nanmax(positive))
            else:
                vmax_plot = float(np.nanpercentile(positive, log_vmax_percentile))
        else:
            vmax_plot = 1.0

        if not np.isfinite(vmax_plot) or vmax_plot <= 0.0:
            vmax_plot = float(np.nanmax(positive)) if positive.size else 1.0
        if not np.isfinite(vmax_plot) or vmax_plot <= 0.0:
            vmax_plot = 1.0

        if vmin is not None:
            vmin_plot = float(vmin)
        else:
            # Fixed dB range relative to the peak.
            # (Intensity is power-like, so use 10*log10 convention.)
            dyn = float(log_dynamic_range_db)
            if not np.isfinite(dyn) or dyn <= 0.0:
                dyn = 60.0
            vmin_plot = vmax_plot / (10.0 ** (dyn / 10.0))

        if not np.isfinite(vmin_plot) or vmin_plot <= 0.0:
            if positive.size:
                vmin_plot = float(np.nanmin(positive[positive > 0.0]))
            else:
                vmin_plot = max(vmax_plot * 1e-12, 1e-12)

        if vmax_plot <= vmin_plot:
            vmax_plot = max(vmin_plot * 10.0, vmin_plot + 1e-12)

        # Clip in the *normalizer* rather than clipping the data array. This preserves
        # the real dynamic range for debugging, while still producing stable visuals.
        norm = colors.LogNorm(vmin=vmin_plot, vmax=vmax_plot, clip=True)

    plot_values_arr = np.array(data, copy=True)
    plot_values_arr[~np.isfinite(plot_values_arr)] = np.nan
    if scale == "log":
        # Log scales can't display zeros/negatives. Instead of masking them (which tends
        # to render as white/transparent), floor them to vmin so the background uses the
        # bottom colormap color.
        plot_values_arr = np.where(plot_values_arr > 0.0, plot_values_arr, vmin_plot)
    elif clip_data:
        plot_values_arr = np.clip(plot_values_arr, vmin_plot, vmax_plot)

    plot_values = np.ma.masked_invalid(plot_values_arr)

    plt = load_pyplot()
    fig, ax = plt.subplots(figsize=figsize)
    mesh = ax.pcolormesh(
        x_axis,
        y_axis,
        plot_values,
        shading="auto",
        cmap=cmap,
        vmin=None if norm is not None else vmin_plot,
        vmax=None if norm is not None else vmax_plot,
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
