from __future__ import annotations

import numpy as np

from cpa_sim.models.config import AmpCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.amp.utils import field_gain_from_power_gain
from cpa_sim.stages.base import LaserStage


class SimpleGainStage(LaserStage[AmpCfg]):
    def __init__(self, cfg: AmpCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        gain = field_gain_from_power_gain(self.cfg.gain_linear)
        out.pulse.field_t = out.pulse.field_t * gain
        out.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(out.pulse.field_t)))
        out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
        out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2
        stage_metrics = {
            f"{self.name}.gain_linear": float(self.cfg.gain_linear),
            f"{self.name}.energy_au": float(np.sum(out.pulse.intensity_t) * out.pulse.grid.dt),
        }
        out.metrics.update(stage_metrics)
        return StageResult(state=out, metrics=stage_metrics)
