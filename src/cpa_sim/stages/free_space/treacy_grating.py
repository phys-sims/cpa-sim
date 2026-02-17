from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FreeSpaceCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class TreacyGratingStage(LaserStage[FreeSpaceCfg]):
    def __init__(self, cfg: FreeSpaceCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        w = np.asarray(out.pulse.grid.w)
        w0 = float(np.mean(w))
        phase = -0.5 * self.cfg.gdd_fs2 * (w - w0) ** 2
        out.pulse.field_w = out.pulse.field_w * np.exp(1j * phase)
        out.pulse.field_t = np.fft.fftshift(np.fft.ifft(np.fft.ifftshift(out.pulse.field_w)))
        out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
        out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2
        stage_metrics = {
            f"{self.name}.energy_au": float(np.sum(out.pulse.intensity_t) * out.pulse.grid.dt),
            f"{self.name}.gdd_fs2": float(self.cfg.gdd_fs2),
        }
        out.metrics.update(stage_metrics)
        return StageResult(state=out, metrics=stage_metrics)
