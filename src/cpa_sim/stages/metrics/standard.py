from __future__ import annotations

import numpy as np

from cpa_sim.models.config import MetricsCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class StandardMetricsStage(LaserStage[MetricsCfg]):
    def __init__(self, cfg: MetricsCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        t = np.asarray(out.pulse.grid.t)
        intensity = out.pulse.intensity_t
        spec = out.pulse.spectrum_w

        energy = float(np.sum(intensity) * out.pulse.grid.dt)
        peak = float(np.max(intensity))
        half = peak / 2.0
        above = np.where(intensity >= half)[0]
        fwhm = float(t[above[-1]] - t[above[0]]) if above.size > 1 else 0.0
        bandwidth = float(np.sqrt(np.average((np.asarray(out.pulse.grid.w) ** 2), weights=spec)))

        stage_metrics = {
            "summary.energy_au": energy,
            "summary.peak_intensity_au": peak,
            "summary.fwhm_fs": fwhm,
            "summary.bandwidth_rad_per_fs": bandwidth,
        }
        out.metrics.update(stage_metrics)
        return StageResult(state=out, metrics=stage_metrics)
