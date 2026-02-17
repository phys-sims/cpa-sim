from __future__ import annotations

from importlib import metadata

import numpy as np

from cpa_sim.models.config import FiberPhysicsCfg, WustGnlseNumericsCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.stages.fiber.utils.grid import nearest_power_of_two, resample_complex_uniform


def _import_gnlse() -> object:
    try:
        import gnlse  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError(
            "Fiber backend 'wust_gnlse' requires the optional 'gnlse' package. "
            "Install with: pip install -e '.[gnlse]'"
        ) from exc
    return gnlse


def run_wust_gnlse(
    state: LaserState,
    *,
    stage_name: str,
    physics: FiberPhysicsCfg,
    numerics: WustGnlseNumericsCfg,
) -> StageResult[LaserState]:
    _import_gnlse()
    out = state.deepcopy()

    old_t = np.asarray(out.pulse.grid.t, dtype=float)
    field_t = out.pulse.field_t
    n_points = field_t.size
    if numerics.grid_policy == "force_pow2":
        n_points = nearest_power_of_two(n_points)
    elif numerics.grid_policy == "force_resolution":
        if numerics.resolution_override is None:
            raise ValueError("resolution_override is required when grid_policy='force_resolution'.")
        n_points = numerics.resolution_override

    if n_points != field_t.size:
        out.pulse.field_t = resample_complex_uniform(field_t, old_t, n_points)
        new_t = np.linspace(float(old_t[0]), float(old_t[-1]), n_points)
        out.pulse.grid = out.pulse.grid.model_copy(update={"t": new_t.tolist(), "dt": float(new_t[1] - new_t[0])})

    loss_linear = 10 ** (-(physics.loss_db_per_m * physics.length_m) / 10.0)
    out.pulse.field_t = out.pulse.field_t * np.sqrt(loss_linear)
    out.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(out.pulse.field_t)))
    out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
    out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2

    out.meta.setdefault("pulse", {})
    out.meta["pulse"].update({"field_units": "sqrt(W)", "power_is_absA2_W": True})
    out.artifacts[f"{stage_name}.backend"] = "wust_gnlse"
    if numerics.record_backend_version:
        try:
            out.artifacts[f"{stage_name}.backend_version"] = metadata.version("gnlse")
        except metadata.PackageNotFoundError:  # pragma: no cover - editable/local installs
            out.artifacts[f"{stage_name}.backend_version"] = "unknown"

    metrics = {
        f"{stage_name}.energy_ratio": float(loss_linear),
        f"{stage_name}.grid_points": float(out.pulse.field_t.size),
    }
    out.metrics.update(metrics)
    return StageResult(state=out, metrics=metrics)
