from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FiberCfg, ToyPhaseNumericsCfg, WustGnlseNumericsCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.stages.fiber.backends.toy_phase import run_toy_phase
from cpa_sim.stages.fiber.backends.wust_gnlse import run_wust_gnlse
from cpa_sim.stages.fiber.utils.grid import assert_uniform_spacing
from cpa_sim.utils import maybe_emit_stage_plots


class FiberStage(LaserStage[FiberCfg]):
    def __init__(self, cfg: FiberCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        self._validate_state(state)
        numerics = self.cfg.numerics
        if isinstance(numerics, ToyPhaseNumericsCfg):
            result = run_toy_phase(
                state,
                stage_name=self.name,
                _physics=self.cfg.physics,
                numerics=numerics,
            )
            result.state.artifacts.update(
                maybe_emit_stage_plots(stage_name=self.name, state=result.state, policy=policy)
            )
            return result
        if isinstance(numerics, WustGnlseNumericsCfg):
            result = run_wust_gnlse(
                state,
                stage_name=self.name,
                physics=self.cfg.physics,
                numerics=numerics,
            )
            result.state.artifacts.update(
                maybe_emit_stage_plots(stage_name=self.name, state=result.state, policy=policy)
            )
            return result
        raise ValueError(f"Unsupported fiber numerics backend: {type(numerics).__name__}")

    def _validate_state(self, state: LaserState) -> None:
        t = np.asarray(state.pulse.grid.t, dtype=float)
        assert_uniform_spacing(t)
