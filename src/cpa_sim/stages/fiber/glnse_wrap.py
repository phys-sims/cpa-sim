from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FiberCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class GNLSEWrapStage(LaserStage[FiberCfg]):
    """Thin deterministic v1 placeholder adapter boundary for external GLNSE backend."""

    def __init__(self, cfg: FiberCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        intensity = np.abs(out.pulse.field_t) ** 2
        phase = self.cfg.nonlinear_phase_rad * intensity / max(float(np.max(intensity)), 1e-12)
        out.pulse.field_t = out.pulse.field_t * np.exp(1j * phase)
        out.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(out.pulse.field_t)))
        out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
        out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2
        stage_metrics = {f"{self.name}.b_integral_proxy_rad": float(np.max(phase))}
        out.metrics.update(stage_metrics)
        return StageResult(state=out, metrics=stage_metrics)
