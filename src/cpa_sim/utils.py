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
    ax.plot(t_fs, state.pulse.intensity_t)
    ax.set_xlabel("Time (fs)")
    ax.set_ylabel("Intensity (|A|^2)")
    ax.set_title(f"Stage: {stage_name} time-domain intensity")
    fig.tight_layout()
    fig.savefig(time_path, format="svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(w, state.pulse.spectrum_w)
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
