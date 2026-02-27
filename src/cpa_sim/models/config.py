from __future__ import annotations

import math
import warnings
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cpa_sim.models.state import LaserSpec, PulseSpec
from cpa_sim.phys_pipeline_compat import StageConfig


def recommended_n_samples_for_pulse(
    *,
    width_fs: float,
    time_window_fs: float,
    min_points_per_fwhm: int = 24,
    prefer_power_of_two: bool = True,
) -> int:
    """Return a sampling count that resolves FWHM with at least ``min_points_per_fwhm``."""
    if width_fs <= 0.0:
        raise ValueError("width_fs must be > 0 for sampling recommendations.")
    if time_window_fs <= 0.0:
        raise ValueError("time_window_fs must be > 0 for sampling recommendations.")
    if min_points_per_fwhm < 1:
        raise ValueError("min_points_per_fwhm must be >= 1.")

    max_dt_fs = width_fs / float(min_points_per_fwhm)
    min_samples = int(math.ceil(time_window_fs / max_dt_fs)) + 1
    min_samples = max(2, min_samples)
    if not prefer_power_of_two:
        return min_samples
    return 1 << (min_samples - 1).bit_length()


def validate_pulse_sampling(
    pulse: PulseSpec,
    *,
    min_points_per_fwhm: int = 24,
    nyquist_margin: float = 3.0,
    min_window_fwhm_ratio: float = 6.0,
    strict: bool = False,
) -> None:
    """Validate temporal sampling policy for analytic pulse generation.

    Enforces ``dt_fs <= width_fs / min_points_per_fwhm`` and optionally checks
    simple Nyquist/window margins that depend on pulse shape.
    """
    if pulse.n_samples < 2:
        raise ValueError("PulseSpec.n_samples must be >= 2 for sampling checks.")
    dt_fs = pulse.time_window_fs / float(pulse.n_samples - 1)
    max_dt_fs = pulse.width_fs / float(min_points_per_fwhm)

    if dt_fs > max_dt_fs:
        message = (
            "Pulse sampling policy violated: dt_fs must satisfy dt_fs <= width_fs / N_min. "
            f"Got dt_fs={dt_fs:.3f} fs with width_fs={pulse.width_fs:.3f} fs and "
            f"N_min={min_points_per_fwhm}. Increase n_samples or reduce time_window_fs."
        )
        if strict:
            raise ValueError(message)
        warnings.warn(message, stacklevel=2)

    width_over_window = pulse.time_window_fs / pulse.width_fs
    if width_over_window < min_window_fwhm_ratio:
        message = (
            "Pulse time window may be too tight for clean FFT tails: "
            f"time_window_fs/width_fs={width_over_window:.2f} < {min_window_fwhm_ratio:.2f}."
        )
        if strict:
            raise ValueError(message)
        warnings.warn(message, stacklevel=2)

    if pulse.shape == "gaussian":
        sigma_fs = pulse.width_fs / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        omega_scale_rad_per_fs = 1.0 / sigma_fs
    else:
        t0_fs = pulse.width_fs / (2.0 * math.acosh(math.sqrt(2.0)))
        omega_scale_rad_per_fs = 1.0 / t0_fs

    nyquist_rad_per_fs = math.pi / dt_fs
    required_nyquist_rad_per_fs = nyquist_margin * omega_scale_rad_per_fs
    if nyquist_rad_per_fs < required_nyquist_rad_per_fs:
        message = (
            "Pulse spectral Nyquist margin is low for the requested pulse shape: "
            f"pi/dt={nyquist_rad_per_fs:.4f} rad/fs < {nyquist_margin:.2f} * "
            f"omega_scale={omega_scale_rad_per_fs:.4f} rad/fs."
        )
        if strict:
            raise ValueError(message)
        warnings.warn(message, stacklevel=2)


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
    loss_db_per_m: float = Field(
        default=0.0,
        description=(
            "Net distributed power attenuation coefficient in dB/m. "
            "Positive values attenuate power and negative values represent distributed gain."
        ),
    )
    gamma_1_per_w_m: float | None = None
    n2_m2_per_w: float | None = None
    aeff_m2: float | None = None
    dispersion: DispersionCfg = Field(
        default_factory=lambda: DispersionTaylorCfg(betas_psn_per_m=[0.0])
    )
    raman: RamanCfg | None = None
    self_steepening: bool = False
    validate_physical_units: bool = True

    @field_validator("loss_db_per_m")
    @classmethod
    def _validate_loss_db_per_m(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("FiberPhysicsCfg.loss_db_per_m must be finite.")
        return value


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


class FiberCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "fiber"
    kind: Literal["fiber"] = "fiber"
    physics: FiberPhysicsCfg = Field(default_factory=FiberPhysicsCfg)
    numerics: FiberNumericsCfg = Field(default_factory=ToyPhaseNumericsCfg)


class FiberAmpWrapCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "amp"
    kind: Literal["fiber_amp_wrap"] = "fiber_amp_wrap"
    physics: FiberPhysicsCfg = Field(default_factory=FiberPhysicsCfg)
    numerics: FiberNumericsCfg = Field(default_factory=ToyPhaseNumericsCfg)
    power_out_w: float

    @field_validator("power_out_w")
    @classmethod
    def _validate_power_out_w(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("FiberAmpWrapCfg.power_out_w must be > 0.")
        return value


class SimpleGainCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str = "amp"
    kind: Literal["simple_gain"] = "simple_gain"
    gain_linear: float = 1.0


AmpStageCfg = Annotated[
    SimpleGainCfg | FiberAmpWrapCfg,
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
