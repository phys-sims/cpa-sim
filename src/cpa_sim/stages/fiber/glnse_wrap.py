from __future__ import annotations

from cpa_sim.models.config import FiberCfg
from cpa_sim.stages.fiber.fiber_stage import FiberStage


class GNLSEWrapStage(FiberStage):
    """Compatibility alias for legacy v1 placeholder backend name."""

    def __init__(self, cfg: FiberCfg):
        super().__init__(cfg)
