from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FiberAmpWrapCfg, FiberCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.stages.fiber import FiberStage

_FS_TO_S = 1e-15


class FiberAmpWrapStage(LaserStage[FiberAmpWrapCfg]):
    """Power-target wrapper around ``FiberStage``.

    The wrapper translates a target average output power into an effective
    distributed loss term and delegates all propagation/numerics to
    ``FiberStage``.
    """

    def __init__(self, cfg: FiberAmpWrapCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        rep_rate_hz = _rep_rate_hz(state.meta)

        energy_in_j = _pulse_energy_j(state)
        power_in_avg_w = energy_in_j * rep_rate_hz
        if power_in_avg_w <= 0.0:
            raise ValueError(
                "FiberAmpWrapStage requires positive input average power; check pulse "
                "normalization/windowing and meta['rep_rate_mhz']."
            )

        length_m = float(self.cfg.physics.length_m)
        if length_m <= 0.0:
            raise ValueError("FiberAmpWrapStage requires physics.length_m > 0.")

        g_net = float(self.cfg.power_out_w / power_in_avg_w)
        if g_net <= 0.0:
            raise ValueError(
                "FiberAmpWrapStage computed non-positive net gain from power_out_w / "
                "power_in_avg_w."
            )

        intrinsic_loss_db_per_m = float(self.cfg.physics.loss_db_per_m)
        target_total_loss_db_per_m = float(-(10.0 / length_m) * np.log10(g_net))
        loss_eff_db_per_m = target_total_loss_db_per_m - intrinsic_loss_db_per_m
        loss_total_db_per_m = intrinsic_loss_db_per_m + loss_eff_db_per_m

        wrapped_physics = self.cfg.physics.model_copy(
            update={"loss_db_per_m": loss_total_db_per_m}, deep=True
        )
        wrapped_cfg = FiberCfg(
            name=self.cfg.name,
            physics=wrapped_physics,
            numerics=self.cfg.numerics.model_copy(deep=True),
        )

        fiber_result = FiberStage(wrapped_cfg).process(state, policy=policy)

        energy_out_j = _pulse_energy_j(fiber_result.state)
        power_out_avg_w = energy_out_j * rep_rate_hz

        stage_metrics = {
            f"{self.name}.power_out_target_w": float(self.cfg.power_out_w),
            f"{self.name}.power_in_avg_w": power_in_avg_w,
            f"{self.name}.power_out_avg_w": power_out_avg_w,
            f"{self.name}.energy_in_j": energy_in_j,
            f"{self.name}.energy_out_j": energy_out_j,
            f"{self.name}.derived_gain_db": float(10.0 * np.log10(g_net)),
            f"{self.name}.derived_loss_eff_db_per_m": loss_eff_db_per_m,
            f"{self.name}.derived_loss_total_db_per_m": loss_total_db_per_m,
        }
        fiber_result.state.metrics.update(stage_metrics)
        merged_metrics = {**fiber_result.metrics, **stage_metrics}
        return StageResult(state=fiber_result.state, metrics=merged_metrics)


def _pulse_energy_j(state: LaserState) -> float:
    intensity = np.abs(np.asarray(state.pulse.field_t, dtype=np.complex128)) ** 2
    dt_fs = float(state.pulse.grid.dt)
    dt_s = dt_fs * _FS_TO_S
    return float(np.sum(intensity) * dt_s)


def _rep_rate_hz(meta: dict[str, object]) -> float:
    rep_rate_mhz = meta.get("rep_rate_mhz")
    if not isinstance(rep_rate_mhz, (float, int)):
        raise ValueError(
            "FiberAmpWrapStage requires state.meta['rep_rate_mhz'] to be present and > 0."
        )
    rep_rate_hz = float(rep_rate_mhz) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("FiberAmpWrapStage requires state.meta['rep_rate_mhz'] > 0.")
    return rep_rate_hz
