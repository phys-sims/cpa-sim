from __future__ import annotations

import numpy as np

from cpa_sim.models.config import FiberAmpWrapCfg, FiberCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.stages.fiber import FiberStage

_FS_TO_S = 1e-15


class FiberAmpWrapStage(LaserStage[FiberAmpWrapCfg]):
    """Lab-friendly fiber amplifier wrapper using FiberStage physics/numerics.

    This wrapper computes a net distributed gain from desired measurement-plane
    average output power and maps it to a negative ``loss_db_per_m`` before
    delegating propagation to ``FiberStage``.
    """

    def __init__(self, cfg: FiberAmpWrapCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        rep_rate_hz = _rep_rate_hz(state.meta)
        power_in_avg_w = _avg_power_w(state, rep_rate_hz=rep_rate_hz)
        if power_in_avg_w <= 0.0:
            raise ValueError(
                "FiberAmpWrapStage requires positive input average power to map power_out_w."
            )

        length_m = self.cfg.physics.length_m
        if length_m <= 0.0:
            raise ValueError("FiberAmpWrapStage requires physics.length_m > 0.")

        net_gain_db = float(10.0 * np.log10(self.cfg.power_out_w / power_in_avg_w))
        effective_loss_db_per_m = -net_gain_db / length_m

        wrapped_physics = self.cfg.physics.model_copy(
            update={"loss_db_per_m": effective_loss_db_per_m}
        )
        wrapped_cfg = FiberCfg(
            name=self.cfg.name, physics=wrapped_physics, numerics=self.cfg.numerics
        )

        fiber_result = FiberStage(wrapped_cfg).process(state, policy=policy)
        achieved_power_out_w = _avg_power_w(fiber_result.state, rep_rate_hz=rep_rate_hz)
        if achieved_power_out_w <= 0.0:
            raise ValueError("FiberAmpWrapStage produced non-positive output average power.")

        field_scale = float(np.sqrt(self.cfg.power_out_w / achieved_power_out_w))
        fiber_result.state.pulse.field_t = fiber_result.state.pulse.field_t * field_scale
        fiber_result.state.pulse.field_w = np.fft.fftshift(
            np.fft.fft(np.fft.ifftshift(fiber_result.state.pulse.field_t))
        )
        fiber_result.state.pulse.intensity_t = np.abs(fiber_result.state.pulse.field_t) ** 2
        fiber_result.state.pulse.spectrum_w = np.abs(fiber_result.state.pulse.field_w) ** 2
        achieved_power_out_w = _avg_power_w(fiber_result.state, rep_rate_hz=rep_rate_hz)

        stage_metrics = {
            f"{self.name}.power_in_avg_w": power_in_avg_w,
            f"{self.name}.power_out_target_w": float(self.cfg.power_out_w),
            f"{self.name}.power_out_avg_w": achieved_power_out_w,
            f"{self.name}.effective_loss_db_per_m": effective_loss_db_per_m,
            f"{self.name}.net_gain_db": net_gain_db,
        }
        fiber_result.state.metrics.update(stage_metrics)
        return StageResult(state=fiber_result.state, metrics=stage_metrics)


def _avg_power_w(state: LaserState, *, rep_rate_hz: float) -> float:
    intensity = np.abs(np.asarray(state.pulse.field_t, dtype=np.complex128)) ** 2
    energy_j = float(np.sum(intensity) * state.pulse.grid.dt * _FS_TO_S)
    return energy_j * rep_rate_hz


def _rep_rate_hz(meta: dict[str, object]) -> float:
    rep_rate_mhz = meta.get("rep_rate_mhz")
    if not isinstance(rep_rate_mhz, (float, int)):
        raise ValueError("FiberAmpWrapStage requires meta['rep_rate_mhz'] in state.meta.")
    rep_rate_hz = float(rep_rate_mhz) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("FiberAmpWrapStage requires rep_rate_mhz > 0.")
    return rep_rate_hz
