from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models.plotting_policy import (
    HeatmapNormPolicy,
    HeatmapWindowPolicy,
    LineWindowPolicy,
    PlotWindowPolicy,
)


@dataclass(frozen=True)
class LineSeries:
    x: np.ndarray
    y: np.ndarray
    label: str


@dataclass(frozen=True)
class HeatmapRenderParams:
    values: np.ndarray
    vmin: float
    vmax: float
    norm: Any | None


def load_pyplot() -> Any:
    matplotlib: Any = import_module("matplotlib")
    matplotlib.use("Agg")
    return import_module("matplotlib.pyplot")


def autoscale_window_1d(
    *,
    x_axis: np.ndarray,
    values: np.ndarray,
    threshold_fraction: float | None = None,
    min_support_width: float | None = None,
    pad_fraction: float | None = None,
    policy: LineWindowPolicy | PlotWindowPolicy | None = None,
) -> tuple[float, float] | None:
    if x_axis.size == 0 or values.size == 0:
        return None

    resolved = policy.line if isinstance(policy, PlotWindowPolicy) else policy
    line_policy = resolved if isinstance(resolved, LineWindowPolicy) else LineWindowPolicy()
    threshold = line_policy.threshold_fraction if threshold_fraction is None else threshold_fraction
    minimum_width = (
        line_policy.min_support_width if min_support_width is None else min_support_width
    )
    pad = line_policy.pad_fraction if pad_fraction is None else pad_fraction

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

    support = np.where(y >= peak * threshold)[0]
    if support.size == 0:
        return (float(np.min(x)), float(np.max(x)))

    lo = float(np.min(x[support]))
    hi = float(np.max(x[support]))
    axis_span = float(np.max(x) - np.min(x))
    support_span = hi - lo
    target_span = max(support_span, float(max(minimum_width, 0.0)))

    if target_span <= 0.0:
        fallback_span = axis_span if axis_span > 0.0 else 1.0
        return (lo - 0.5 * fallback_span, hi + 0.5 * fallback_span)

    center = 0.5 * (lo + hi)
    lo = center - 0.5 * target_span
    hi = center + 0.5 * target_span
    padded = pad * target_span
    return (lo - padded, hi + padded)


def auto_xlim_from_intensity(
    x: np.ndarray,
    intensity_2d: np.ndarray,
    *,
    coverage: float | None = None,
    pad_frac: float | None = None,
    axis_for_x: int = -1,
    policy: HeatmapWindowPolicy | PlotWindowPolicy | None = None,
) -> tuple[float, float]:
    """Estimate a robust x-axis window from 2D intensity support."""
    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim != 1 or x_arr.size == 0:
        raise ValueError("x must be a non-empty 1D array.")

    resolved = policy.heatmap if isinstance(policy, PlotWindowPolicy) else policy
    heatmap_policy = (
        resolved if isinstance(resolved, HeatmapWindowPolicy) else HeatmapWindowPolicy()
    )
    coverage_value = heatmap_policy.coverage_quantile if coverage is None else coverage
    pad_value = heatmap_policy.pad_fraction if pad_frac is None else pad_frac

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
    if profile.size:
        baseline = float(np.nanquantile(profile, 0.2))
        if np.isfinite(baseline) and baseline > 0.0:
            profile = np.clip(profile - baseline, 0.0, None)

    x_min = float(np.nanmin(x_arr))
    x_max = float(np.nanmax(x_arr))
    total = float(np.sum(profile))
    if not np.isfinite(total) or total <= 0.0:
        if heatmap_policy.fallback_behavior == "line_window":
            xlim = autoscale_window_1d(x_axis=x_arr, values=profile)
            return (x_min, x_max) if xlim is None else xlim
        return x_min, x_max

    order = np.argsort(x_arr)
    x_sorted = x_arr[order]
    p_sorted = profile[order]
    total = float(np.sum(p_sorted))
    if total <= 0.0:
        if heatmap_policy.fallback_behavior == "line_window":
            xlim = autoscale_window_1d(x_axis=x_arr, values=profile)
            return (x_min, x_max) if xlim is None else xlim
        return x_min, x_max

    cdf = np.cumsum(p_sorted) / total
    clipped_coverage = float(np.clip(coverage_value, 1e-9, 1.0))
    lo_q = (1.0 - clipped_coverage) / 2.0
    hi_q = 1.0 - lo_q
    lo = float(np.interp(lo_q, cdf, x_sorted))
    hi = float(np.interp(hi_q, cdf, x_sorted))

    if not np.isfinite(lo) or not np.isfinite(hi) or hi < lo:
        return x_min, x_max

    span = hi - lo
    if span <= 0.0:
        return x_min, x_max
    pad = pad_value * span
    return lo - pad, hi + pad


def resolve_heatmap_render_params(
    *,
    values: np.ndarray,
    scale: str | None = None,
    policy: HeatmapNormPolicy | PlotWindowPolicy | None = None,
    symmetric: bool = False,
) -> HeatmapRenderParams:
    norm_policy = policy.heatmap_norm if isinstance(policy, PlotWindowPolicy) else policy
    resolved = norm_policy if isinstance(norm_policy, HeatmapNormPolicy) else HeatmapNormPolicy()

    scale_mode = resolved.scale if scale is None else scale
    if scale_mode not in {"linear", "log"}:
        raise ValueError(f"Unsupported heatmap scale '{scale_mode}'.")

    data = np.asarray(values, dtype=float)
    finite = data[np.isfinite(data)]

    if scale_mode == "linear":
        if symmetric:
            abs_data = np.abs(finite)
            max_abs = (
                float(np.nanpercentile(abs_data, resolved.vmax_percentile))
                if abs_data.size
                else 1.0
            )
            if not np.isfinite(max_abs) or max_abs <= 0.0:
                max_abs = float(np.max(abs_data)) if abs_data.size else 1.0
            if not np.isfinite(max_abs) or max_abs <= 0.0:
                max_abs = 1.0
            vmin = -max_abs
            vmax = max_abs
            clipped = np.clip(np.where(np.isfinite(data), data, 0.0), vmin, vmax)
            return HeatmapRenderParams(values=clipped, vmin=vmin, vmax=vmax, norm=None)

        lower = float(np.clip(resolved.vmin_percentile, 0.0, 100.0))
        upper = float(np.clip(resolved.vmax_percentile, lower, 100.0))
        positive = finite[finite >= 0.0]
        source = positive if positive.size else finite

        vmin = float(np.nanpercentile(source, lower)) if source.size else 0.0
        vmax = float(np.nanpercentile(source, upper)) if source.size else 1.0

        if not np.isfinite(vmin):
            vmin = 0.0
        if not np.isfinite(vmax) or vmax <= vmin:
            vmax = float(np.nanmax(source)) if source.size else 1.0
        if not np.isfinite(vmax) or vmax <= vmin:
            vmax = vmin + 1.0

        clipped = np.clip(np.where(np.isfinite(data), data, vmin), vmin, vmax)
        gamma = max(float(resolved.gamma), 1e-12)
        if abs(gamma - 1.0) > 1e-12:
            normalized = (clipped - vmin) / (vmax - vmin)
            adjusted = np.power(np.clip(normalized, 0.0, 1.0), gamma)
            clipped = vmin + adjusted * (vmax - vmin)
        return HeatmapRenderParams(values=clipped, vmin=vmin, vmax=vmax, norm=None)

    colors = import_module("matplotlib.colors")
    positive = finite[finite > 0.0]
    peak = float(np.max(positive)) if positive.size else 1.0
    if not np.isfinite(peak) or peak <= 0.0:
        peak = 1.0
    dynamic_range_db = max(float(resolved.dynamic_range_db), 1e-9)
    floor = peak * 10.0 ** (-dynamic_range_db / 10.0)
    vmin = max(floor, float(np.min(positive)) if positive.size else floor)
    vmax = peak
    if not np.isfinite(vmin) or vmin <= 0.0:
        vmin = peak * 1e-6
    if not np.isfinite(vmax) or vmax <= vmin:
        vmax = max(vmin * 10.0, 1e-11)
    clipped = np.clip(np.where(np.isfinite(data), data, vmin), vmin, vmax)
    norm = colors.LogNorm(vmin=vmin, vmax=vmax)
    return HeatmapRenderParams(values=clipped, vmin=vmin, vmax=vmax, norm=norm)


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
    plot_policy: PlotWindowPolicy | None = None,
) -> Path:
    plt = load_pyplot()

    fig, ax = plt.subplots(figsize=figsize)
    for entry in series:
        x = np.asarray(entry.x, dtype=float)
        y = np.asarray(entry.y, dtype=float)
        ax.plot(x, y, label=entry.label)

    if auto_xlim and series:
        xlim = autoscale_window_1d(
            x_axis=np.asarray(series[0].x, dtype=float),
            values=np.asarray(series[0].y, dtype=float),
            policy=plot_policy,
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
    scale: str | None = None,
    xlim: str | tuple[float, float] | None = "auto",
    axis_for_x: int = -1,
    figsize: tuple[float, float] = (8, 4.8),
    plot_policy: PlotWindowPolicy | None = None,
) -> Path:
    render = resolve_heatmap_render_params(values=values, scale=scale, policy=plot_policy)

    plt = load_pyplot()
    fig, ax = plt.subplots(figsize=figsize)
    mesh = ax.pcolormesh(
        x_axis,
        y_axis,
        render.values,
        shading="auto",
        cmap=cmap,
        vmin=None if render.norm is not None else render.vmin,
        vmax=None if render.norm is not None else render.vmax,
        norm=render.norm,
    )
    fig.colorbar(mesh, ax=ax, label=color_label)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    if xlim == "auto":
        ax.set_xlim(
            auto_xlim_from_intensity(
                x_axis,
                values,
                axis_for_x=axis_for_x,
                policy=plot_policy,
            )
        )
    elif xlim is not None:
        ax.set_xlim(xlim)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    return out_path
