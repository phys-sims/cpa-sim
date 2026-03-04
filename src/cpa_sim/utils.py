from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag


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

    try:
        plt: Any = import_module("matplotlib.pyplot")
    except ModuleNotFoundError:
        return {}

    t_fs = np.asarray(state.pulse.grid.t, dtype=float)
    w = np.asarray(state.pulse.grid.w, dtype=float)

    time_path = out_dir / f"{stage_name}_time_intensity.svg"
    spectrum_path = out_dir / f"{stage_name}_spectrum.svg"

    fig, ax = plt.subplots(figsize=(8, 4.5))
    intensity_t = np.asarray(state.pulse.intensity_t, dtype=float)
    ax.plot(t_fs, intensity_t)
    time_xlim = _autoscale_window(x_axis=t_fs, values=intensity_t)
    if time_xlim is not None:
        ax.set_xlim(*time_xlim)
    ax.set_xlabel("Time (fs)")
    ax.set_ylabel("Intensity (|A|^2)")
    ax.set_title(f"Stage: {stage_name} time-domain intensity")
    fig.tight_layout()
    fig.savefig(time_path, format="svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    spectrum_w = np.asarray(state.pulse.spectrum_w, dtype=float)
    ax.plot(w, spectrum_w)
    spectrum_xlim = _autoscale_window(x_axis=w, values=spectrum_w)
    if spectrum_xlim is not None:
        ax.set_xlim(*spectrum_xlim)
    ax.set_xlabel("Angular frequency (rad/fs)")
    ax.set_ylabel("Spectrum (|Aw|^2)")
    ax.set_title(f"Stage: {stage_name} spectral magnitude")
    fig.tight_layout()
    fig.savefig(spectrum_path, format="svg")
    plt.close(fig)

    return {
        f"{stage_name}.plot_time_intensity": str(time_path),
        f"{stage_name}.plot_spectrum": str(spectrum_path),
    }


def _autoscale_window(
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
