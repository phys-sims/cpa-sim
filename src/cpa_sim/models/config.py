from __future__ import annotations

from typing import Annotated, Literal

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


class DispersionTaylorCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["taylor"] = "taylor"
    betas_psn_per_m: list[float]


class DispersionInterpolationCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["interpolation"] = "interpolation"
    effective_indices: list[float]
    lambdas_nm: list[float]
    central_wavelength_nm: float


DispersionCfg = Annotated[
    DispersionTaylorCfg | DispersionInterpolationCfg,
    Field(discriminator="kind"),
]


class RamanCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["wust"] = "wust"
    model: Literal["blowwood", "linagrawal", "hollenbeck"]


class FiberPhysicsCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    length_m: float = 1.0
    loss_db_per_m: float = 0.0
    gamma_1_per_w_m: float | None = None
    n2_m2_per_w: float | None = None
    aeff_m2: float | None = None
    dispersion: DispersionCfg = Field(
        default_factory=lambda: DispersionTaylorCfg(betas_psn_per_m=[0.0])
    )
    raman: RamanCfg | None = None
    self_steepening: bool = False
    validate_physical_units: bool = True


class ToyPhaseNumericsCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend: Literal["toy_phase"] = "toy_phase"
    nonlinear_phase_rad: float = 0.0


class WustGnlseNumericsCfg(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend: Literal["wust_gnlse"] = "wust_gnlse"
    grid_policy: Literal["use_state", "force_pow2", "force_resolution"] = "use_state"
    resolution_override: int | None = None
    time_window_override_ps: float | None = None
    z_saves: int = 200
    method: str = "RK45"
    rtol: float = 1e-5
    atol: float = 1e-8
    keep_full_solution: bool = False
    keep_aw: bool = True
    record_backend_version: bool = True


FiberNumericsCfg = Annotated[
    ToyPhaseNumericsCfg | WustGnlseNumericsCfg,
    Field(discriminator="backend"),
]


class FiberStageCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "fiber"
    kind: Literal["fiber"] = "fiber"
    physics: FiberPhysicsCfg = Field(default_factory=FiberPhysicsCfg)
    numerics: FiberNumericsCfg = Field(default_factory=ToyPhaseNumericsCfg)


class FiberCfg(FiberStageCfg):
    """Backwards-compatible alias for pre-Strategy-B configs."""

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_shape(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        legacy_kind = payload.get("kind")
        if legacy_kind == "glnse":
            payload["kind"] = "fiber"
        if "nonlinear_phase_rad" in payload and "numerics" not in payload:
            payload["numerics"] = {
                "backend": "toy_phase",
                "nonlinear_phase_rad": payload.pop("nonlinear_phase_rad"),
            }
        return payload


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
