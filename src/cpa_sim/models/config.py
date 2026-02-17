from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class StageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_type: Literal["laser_gen", "free_space", "fiber", "amp", "metrics"]
    key: str


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: RuntimeCfg = Field(default_factory=RuntimeCfg)

    # Legacy v1 single-stage keys (kept for backwards compatibility).
    laser_gen: LaserGenCfg = Field(default_factory=LaserGenCfg)
    stretcher: FreeSpaceCfg = Field(default_factory=lambda: FreeSpaceCfg(name="stretcher"))
    fiber: FiberCfg = Field(default_factory=FiberCfg)
    amp: AmpCfg = Field(default_factory=AmpCfg)
    compressor: FreeSpaceCfg = Field(default_factory=lambda: FreeSpaceCfg(name="compressor"))
    metrics: MetricsCfg = Field(default_factory=MetricsCfg)

    # New stage-bank + sequence model for optional/repeated stage topologies.
    laser_gen_stages: dict[str, LaserGenCfg] = Field(default_factory=dict)
    free_space_stages: dict[str, FreeSpaceCfg] = Field(default_factory=dict)
    fiber_stages: dict[str, FiberCfg] = Field(default_factory=dict)
    amp_stages: dict[str, AmpCfg] = Field(default_factory=dict)
    metrics_stages: dict[str, MetricsCfg] = Field(default_factory=dict)
    stage_chain: list[StageRef] | None = None

    @model_validator(mode="after")
    def _populate_stage_banks_and_validate_chain(self) -> PipelineConfig:
        if not self.laser_gen_stages:
            self.laser_gen_stages["laser_init"] = self.laser_gen
        if not self.free_space_stages:
            self.free_space_stages["stretcher"] = self.stretcher
            self.free_space_stages["compressor"] = self.compressor
        if not self.fiber_stages:
            self.fiber_stages["fiber"] = self.fiber
        if not self.amp_stages:
            self.amp_stages["amp"] = self.amp
        if not self.metrics_stages:
            self.metrics_stages["metrics"] = self.metrics

        chain = self.stage_chain or [
            StageRef(stage_type="laser_gen", key="laser_init"),
            StageRef(stage_type="free_space", key="stretcher"),
            StageRef(stage_type="fiber", key="fiber"),
            StageRef(stage_type="amp", key="amp"),
            StageRef(stage_type="free_space", key="compressor"),
            StageRef(stage_type="metrics", key="metrics"),
        ]

        if not chain:
            raise ValueError("stage_chain cannot be empty")
        if chain[0].stage_type != "laser_gen":
            raise ValueError("stage_chain must start with laser_gen")
        if chain[-1].stage_type != "metrics":
            raise ValueError("stage_chain must end with metrics")

        stage_maps: Mapping[str, Mapping[str, StageConfig]] = {
            "laser_gen": self.laser_gen_stages,
            "free_space": self.free_space_stages,
            "fiber": self.fiber_stages,
            "amp": self.amp_stages,
            "metrics": self.metrics_stages,
        }
        for ref in chain:
            if ref.key not in stage_maps[ref.stage_type]:
                raise ValueError(
                    "stage_chain references missing stage key "
                    f"'{ref.key}' for type '{ref.stage_type}'"
                )

        object.__setattr__(self, "stage_chain", chain)
        return self
