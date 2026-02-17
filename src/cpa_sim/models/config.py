from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cpa_sim.models.state import LaserSpec
from cpa_sim.phys_pipeline_compat import StageConfig


class RuntimeCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: int = 0


class LaserGenCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "laser_init"
    kind: Literal["analytic"] = "analytic"
    spec: LaserSpec = Field(default_factory=LaserSpec)


class FreeSpaceCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["treacy_grating"] = "treacy_grating"
    gdd_fs2: float = 0.0


class FiberCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "fiber"
    kind: Literal["glnse"] = "glnse"
    nonlinear_phase_rad: float = 0.0


class AmpCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "amp"
    kind: Literal["simple_gain"] = "simple_gain"
    gain_linear: float = 1.0


class MetricsCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "metrics"
    kind: Literal["standard"] = "standard"


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: RuntimeCfg = Field(default_factory=RuntimeCfg)
    laser_gen: LaserGenCfg = Field(default_factory=LaserGenCfg)
    stretcher: FreeSpaceCfg = Field(default_factory=lambda: FreeSpaceCfg(name="stretcher"))
    fiber: FiberCfg = Field(default_factory=FiberCfg)
    amp: AmpCfg = Field(default_factory=AmpCfg)
    compressor: FreeSpaceCfg = Field(default_factory=lambda: FreeSpaceCfg(name="compressor"))
    metrics: MetricsCfg = Field(default_factory=MetricsCfg)
