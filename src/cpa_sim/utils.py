from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models.plotting_policy import PlotWindowPolicy
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag
from cpa_sim.plotting.common import LineSeries, plot_line_series


def _policy_get(policy: PolicyBag | None, key: str, default: Any = None) -> Any:
    if policy is None:
        return default
    if isinstance(policy, Mapping):
        return policy.get(key, default)
    getter = getattr(policy, "get", None)
    if callable(getter):
        return getter(key, default)
    return default


def maybe_emit_stage_plots(
    *, stage_name: str, state: LaserState, policy: PolicyBag | None
) -> dict[str, str]:
    emit = bool(
        _policy_get(policy, "cpa.emit_stage_plots", False)
        or _policy_get(policy, "emit_stage_plots", False)
    )
    if not emit:
        return {}

    out_dir_value = _policy_get(policy, "cpa.stage_plot_dir", "artifacts/stage-plots")
    out_dir = Path(str(out_dir_value))
    out_dir.mkdir(parents=True, exist_ok=True)

    t_fs = np.asarray(state.pulse.grid.t, dtype=float)
    w = np.asarray(state.pulse.grid.w, dtype=float)
    plot_policy = PlotWindowPolicy.from_policy_bag(policy)

    time_path = out_dir / f"{stage_name}_time_intensity.svg"
    spectrum_path = out_dir / f"{stage_name}_spectrum.svg"

    try:
        plot_line_series(
            out_path=time_path,
            series=[
                LineSeries(
                    x=t_fs,
                    y=np.asarray(state.pulse.intensity_t, dtype=float),
                    label="",
                )
            ],
            x_label="Time (fs)",
            y_label="Intensity (|A|^2)",
            title=f"Stage: {stage_name} time-domain intensity",
            plot_format="svg",
            auto_xlim=True,
            plot_policy=plot_policy,
        )
        plot_line_series(
            out_path=spectrum_path,
            series=[
                LineSeries(
                    x=w,
                    y=np.asarray(state.pulse.spectrum_w, dtype=float),
                    label="",
                )
            ],
            x_label="Angular frequency (rad/fs)",
            y_label="Spectrum (|Aw|^2)",
            title=f"Stage: {stage_name} spectral magnitude",
            plot_format="svg",
            auto_xlim=True,
            plot_policy=plot_policy,
        )
    except ModuleNotFoundError:
        return {}

    return {
        f"{stage_name}.plot_time_intensity": str(time_path),
        f"{stage_name}.plot_spectrum": str(spectrum_path),
    }


def maybe_emit_stage_overlay_plots(
    *,
    stage_name: str,
    state: LaserState,
    policy: PolicyBag | None,
    reference_intensity_t: np.ndarray,
    reference_spectrum_w: np.ndarray,
    reference_t_fs: np.ndarray | None = None,
    reference_w_rad_per_fs: np.ndarray | None = None,
    label_reference: str = "Input",
    label_output: str = "Output",
) -> dict[str, str]:
    emit = bool(
        _policy_get(policy, "cpa.emit_stage_plots", False)
        or _policy_get(policy, "emit_stage_plots", False)
    )
    if not emit:
        return {}

    out_dir_value = _policy_get(policy, "cpa.stage_plot_dir", "artifacts/stage-plots")
    out_dir = Path(str(out_dir_value))
    out_dir.mkdir(parents=True, exist_ok=True)

    target_t_fs = np.asarray(state.pulse.grid.t, dtype=float)
    target_w = np.asarray(state.pulse.grid.w, dtype=float)
    target_intensity = np.asarray(state.pulse.intensity_t, dtype=float)
    target_spectrum = np.asarray(state.pulse.spectrum_w, dtype=float)
    plot_policy = PlotWindowPolicy.from_policy_bag(policy)

    ref_time = _resample_reference_series(
        reference_axis=reference_t_fs,
        reference_values=reference_intensity_t,
        target_axis=target_t_fs,
    )
    ref_spectrum = _resample_reference_series(
        reference_axis=reference_w_rad_per_fs,
        reference_values=reference_spectrum_w,
        target_axis=target_w,
    )
    if ref_time is None or ref_spectrum is None:
        return {}

    time_overlay_path = out_dir / f"{stage_name}_time_intensity_overlay.svg"
    spectrum_overlay_path = out_dir / f"{stage_name}_spectrum_overlay.svg"

    try:
        plot_line_series(
            out_path=time_overlay_path,
            series=[
                LineSeries(x=target_t_fs, y=ref_time, label=label_reference),
                LineSeries(x=target_t_fs, y=target_intensity, label=label_output),
            ],
            x_label="Time (fs)",
            y_label="Intensity (|A|^2)",
            title=f"Stage: {stage_name} input vs output time intensity",
            plot_format="svg",
            auto_xlim=True,
            plot_policy=plot_policy,
        )
        plot_line_series(
            out_path=spectrum_overlay_path,
            series=[
                LineSeries(x=target_w, y=ref_spectrum, label=label_reference),
                LineSeries(x=target_w, y=target_spectrum, label=label_output),
            ],
            x_label="Angular frequency (rad/fs)",
            y_label="Spectrum (|Aw|^2)",
            title=f"Stage: {stage_name} input vs output spectrum",
            plot_format="svg",
            auto_xlim=True,
            plot_policy=plot_policy,
        )
    except ModuleNotFoundError:
        return {}

    return {
        f"{stage_name}.plot_time_intensity_overlay": str(time_overlay_path),
        f"{stage_name}.plot_spectrum_overlay": str(spectrum_overlay_path),
    }


def _resample_reference_series(
    *,
    reference_axis: np.ndarray | None,
    reference_values: np.ndarray,
    target_axis: np.ndarray,
) -> np.ndarray | None:
    reference_values_array = np.asarray(reference_values, dtype=float)
    target_axis_array = np.asarray(target_axis, dtype=float)

    if reference_values_array.shape == target_axis_array.shape:
        return reference_values_array
    if reference_axis is None:
        return None

    reference_axis_array = np.asarray(reference_axis, dtype=float)
    if reference_axis_array.shape != reference_values_array.shape:
        return None
    if reference_axis_array.size < 2 or target_axis_array.size < 2:
        return None
    if not _is_strictly_increasing(reference_axis_array):
        return None
    if not _is_strictly_increasing(target_axis_array):
        return None

    return np.interp(
        target_axis_array,
        reference_axis_array,
        reference_values_array,
        left=float(reference_values_array[0]),
        right=float(reference_values_array[-1]),
    )


def _is_strictly_increasing(values: np.ndarray) -> bool:
    if values.ndim != 1 or values.size < 2:
        return False
    diffs = np.diff(values)
    return bool(np.all(np.isfinite(values)) and np.all(diffs > 0.0))
