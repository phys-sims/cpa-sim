from __future__ import annotations

from cpa_sim.models.config import AmpCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage


class EdfaStage(LaserStage[AmpCfg]):
    """Planned v2 EDFA backend placeholder with explicit failure semantics."""

    def __init__(self, cfg: AmpCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        raise NotImplementedError(
            "EDFA backend is planned for v2. Use kind='simple_gain' for v1 runs."
        )
