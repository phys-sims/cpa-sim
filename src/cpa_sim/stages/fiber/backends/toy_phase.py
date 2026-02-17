from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FiberPhysicsCfg, ToyPhaseNumericsCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import StageResult


def run_toy_phase(
    state: LaserState,
    *,
    stage_name: str,
    _physics: FiberPhysicsCfg,
    numerics: ToyPhaseNumericsCfg,
) -> StageResult[LaserState]:
    out = state.deepcopy()
    intensity = np.abs(out.pulse.field_t) ** 2
    phase = numerics.nonlinear_phase_rad * intensity / max(float(np.max(intensity)), 1e-12)
    out.pulse.field_t = out.pulse.field_t * np.exp(1j * phase)
    out.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(out.pulse.field_t)))
    out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
    out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2
    out.meta.setdefault("pulse", {})
    out.meta["pulse"].update({"field_units": "sqrt(W)", "power_is_absA2_W": True})
    metrics = {f"{stage_name}.b_integral_proxy_rad": float(np.max(phase))}
    out.metrics.update(metrics)
    return StageResult(state=out, metrics=metrics)
