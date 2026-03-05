from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag
from cpa_sim.plotting.common import LineSeries, autoscale_window_1d, plot_line_series


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
        )
    except ModuleNotFoundError:
        return {}

    return {
        f"{stage_name}.plot_time_intensity": str(time_path),
        f"{stage_name}.plot_spectrum": str(spectrum_path),
    }


def _autoscale_window(
    *, x_axis: np.ndarray, values: np.ndarray, threshold_fraction: float = 1e-3
) -> tuple[float, float] | None:
    """Backward-compatible alias for shared 1D autoscaling utility."""
    return autoscale_window_1d(
        x_axis=np.asarray(x_axis, dtype=float),
        values=np.asarray(values, dtype=float),
        threshold_fraction=threshold_fraction,
    )
