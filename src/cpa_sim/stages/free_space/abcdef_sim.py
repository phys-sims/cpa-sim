from __future__ import annotations

from cpa_sim.models.config import FreeSpaceCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class AbcdefSimStage(LaserStage[FreeSpaceCfg]):
    """Planned v2 free-space backend placeholder with explicit failure semantics."""

    def __init__(self, cfg: FreeSpaceCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        raise NotImplementedError(
            "abcdef-sim backend is planned for v2. Use kind='treacy_grating' for v1 runs."
        )
