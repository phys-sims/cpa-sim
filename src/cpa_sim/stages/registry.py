from __future__ import annotations

from cpa_sim.models.config import AmpCfg, FiberCfg, FreeSpaceCfg, LaserGenCfg, MetricsCfg
from cpa_sim.stages.amp import SimpleGainStage
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.free_space import TreacyGratingStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage
from cpa_sim.stages.metrics import StandardMetricsStage

LASER_GEN_BACKENDS = {"analytic": AnalyticLaserGenStage}
FREE_SPACE_BACKENDS = {
    "treacy_grating": TreacyGratingStage,
    "phase_only_dispersion": TreacyGratingStage,
    "treacy_grating_pair": TreacyGratingStage,
}
FIBER_BACKENDS = {"fiber": FiberStage}
AMP_BACKENDS = {"simple_gain": SimpleGainStage}
METRICS_BACKENDS = {"standard": StandardMetricsStage}


def build_laser_gen_stage(cfg: LaserGenCfg) -> AnalyticLaserGenStage:
    return LASER_GEN_BACKENDS[cfg.kind](cfg)


def build_free_space_stage(cfg: FreeSpaceCfg) -> TreacyGratingStage:
    return FREE_SPACE_BACKENDS[cfg.kind](cfg)


def build_fiber_stage(cfg: FiberCfg) -> FiberStage:
    return FIBER_BACKENDS[cfg.kind](cfg)


def build_amp_stage(cfg: AmpCfg) -> SimpleGainStage:
    return AMP_BACKENDS[cfg.kind](cfg)


def build_metrics_stage(cfg: MetricsCfg) -> StandardMetricsStage:
    return METRICS_BACKENDS[cfg.kind](cfg)
