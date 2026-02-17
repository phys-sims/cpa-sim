from __future__ import annotations

from cpa_sim.models.config import FiberCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class GnlseSimStage(LaserStage[FiberCfg]):
    """Compatibility alias point for planned v2 gnlse-sim backend."""

    def __init__(self, cfg: FiberCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        raise NotImplementedError(
            "gnlse-sim backend is planned for v2. Use kind='glnse' for v1 runs."
        )
