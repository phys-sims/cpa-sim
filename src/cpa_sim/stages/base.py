from __future__ import annotations

from typing import Generic, TypeVar

from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PipelineStage, StageConfig

CfgT = TypeVar("CfgT", bound=StageConfig)


class LaserStage(PipelineStage[LaserState, CfgT], Generic[CfgT]):
    """Shared base class for cpa-sim stages with a stable `LaserState` payload."""

    version = "v1"
