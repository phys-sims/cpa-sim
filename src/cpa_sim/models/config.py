from __future__ import annotations

import warnings
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class TreacyGratingPairCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["treacy_grating_pair"] = "treacy_grating_pair"
    line_density_lpmm: float = 1200.0
    incidence_angle_deg: float = 35.0
    separation_um: float = 100_000.0
    wavelength_nm: float = 1030.0
    diffraction_order: int = -1
    n_passes: int = 2
    include_tod: bool = True
    apply_to_pulse: bool = True
    override_gdd_fs2: float | None = None
    override_tod_fs3: float | None = None


class PhaseOnlyDispersionCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["phase_only_dispersion"] = "phase_only_dispersion"
    gdd_fs2: float = 0.0
    tod_fs3: float = 0.0
    apply_to_pulse: bool = True


FreeSpaceCfg = Annotated[
    TreacyGratingPairCfg | PhaseOnlyDispersionCfg,
    Field(discriminator="kind"),
]


def _migrate_legacy_free_space_cfg(data: object) -> object:
    if not isinstance(data, dict):
        return data
    if data.get("kind") != "treacy_grating":
        return data
    warnings.warn(
        "Free-space kind='treacy_grating' is deprecated; use kind='phase_only_dispersion' "
        "or kind='treacy_grating_pair'.",
        DeprecationWarning,
        stacklevel=3,
    )
    return {
        "name": data.get("name", "free_space"),
        "kind": "phase_only_dispersion",
        "gdd_fs2": data.get("gdd_fs2", 0.0),
        "tod_fs3": data.get("tod_fs3", 0.0),
        "apply_to_pulse": data.get("apply_to_pulse", True),
    }


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


class SimpleGainCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "amp"
    kind: Literal["simple_gain"] = "simple_gain"
    gain_linear: float = 1.0


class ToyFiberAmpCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "amp"
    kind: Literal["toy_fiber_amp"] = "toy_fiber_amp"
    length_m: float = 1.0
    beta2_s2_per_m: float = 0.0
    gamma_w_inv_m: float = 0.0
    gain_db: float = 0.0
    loss_db_per_m: float = 0.0
    n_steps: int = 8

    @field_validator("length_m")
    @classmethod
    def _validate_length(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("ToyFiberAmpCfg.length_m must be > 0.")
        return value

    @field_validator("n_steps")
    @classmethod
    def _validate_n_steps(cls, value: int) -> int:
        if value < 1:
            raise ValueError("ToyFiberAmpCfg.n_steps must be >= 1.")
        return value


AmpStageCfg = Annotated[
    SimpleGainCfg | ToyFiberAmpCfg,
    Field(discriminator="kind"),
]


PipelineStageCfg = Annotated[
    FreeSpaceCfg | FiberCfg | AmpStageCfg,
    Field(discriminator="kind"),
]


class MetricsCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "metrics"
    kind: Literal["standard"] = "standard"


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: RuntimeCfg = Field(default_factory=RuntimeCfg)
    laser_gen: LaserGenCfg = Field(default_factory=LaserGenCfg)
    stretcher: FreeSpaceCfg = Field(
        default_factory=lambda: PhaseOnlyDispersionCfg(name="stretcher")
    )
    fiber: FiberCfg = Field(default_factory=FiberCfg)
    amp: AmpStageCfg = Field(default_factory=SimpleGainCfg)
    compressor: FreeSpaceCfg = Field(
        default_factory=lambda: TreacyGratingPairCfg(name="compressor")
    )
    stages: list[PipelineStageCfg] | None = None
    metrics: MetricsCfg = Field(default_factory=MetricsCfg)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_free_space(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        for key in ("stretcher", "compressor"):
            if key in payload:
                payload[key] = _migrate_legacy_free_space_cfg(payload[key])
        if "stages" in payload and isinstance(payload["stages"], list):
            payload["stages"] = [
                _migrate_legacy_free_space_cfg(stage_cfg) for stage_cfg in payload["stages"]
            ]
        return payload


# Backwards-compatible alias retained for pre-rename imports.
AmpCfg = SimpleGainCfg
