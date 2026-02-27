from __future__ import annotations

import copy
import hashlib
import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cpa_sim.phys_pipeline_compat import State


class PulseGrid(BaseModel):
    model_config = ConfigDict(frozen=True)

    t: list[float]
    w: list[float]
    dt: float
    dw: float
    center_wavelength_nm: float


class PulseSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape: Literal["gaussian", "sech2"] = Field(
        default="gaussian",
        description=(
            "Pulse intensity profile family in time: 'gaussian' means "
            "I(t) ∝ exp(-4 ln 2 (t/FWHM)^2), 'sech2' means I(t) ∝ sech^2(t/T0)."
        ),
    )
    amplitude: float = Field(
        default=1.0,
        description=(
            "Legacy envelope amplitude scaling in sqrt(W), where instantaneous power is "
            "|E(t)|^2 in W. Deprecated: prefer peak_power_w or avg_power_w."
        ),
        json_schema_extra={"deprecated": True},
    )
    avg_power_w: float | None = Field(
        default=None,
        description="Average power in watts (W).",
    )
    pulse_energy_j: float | None = Field(
        default=None,
        description="Energy per pulse in joules (J).",
    )
    peak_power_w: float | None = Field(
        default=None,
        description="Peak instantaneous power in watts (W).",
    )
    width_fs: float = Field(
        default=100.0,
        description="Intensity full width at half maximum (FWHM) in femtoseconds.",
    )
    intensity_autocorr_fwhm_fs: float | None = Field(
        default=None,
        description=(
            "Intensity autocorrelation FWHM in femtoseconds (fs), as read from an "
            "autocorrelator before shape-dependent deconvolution to pulse intensity FWHM."
        ),
    )
    center_wavelength_nm: float = 1030.0
    rep_rate_mhz: float = 1.0
    n_samples: int = 256
    time_window_fs: float = 2000.0

    @field_validator("rep_rate_mhz")
    @classmethod
    def _validate_rep_rate(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("PulseSpec.rep_rate_mhz must be > 0.")
        return value

    @field_validator(
        "avg_power_w",
        "pulse_energy_j",
        "peak_power_w",
    )
    @classmethod
    def _validate_nonnegative_power_and_energy(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0:
            raise ValueError("PulseSpec power/energy values must be >= 0.")
        return value

    @field_validator("width_fs", "intensity_autocorr_fwhm_fs")
    @classmethod
    def _validate_positive_widths(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0.0:
            raise ValueError("PulseSpec width values must be > 0.")
        return value

    @model_validator(mode="after")
    def _validate_exclusive_inputs(self) -> PulseSpec:
        explicitly_set = set(self.model_fields_set)

        explicit_power_fields = {
            "avg_power_w",
            "pulse_energy_j",
            "peak_power_w",
            "amplitude",
        } & explicitly_set
        if "amplitude" in explicit_power_fields and len(explicit_power_fields) > 1:
            raise ValueError(
                "PulseSpec.amplitude cannot be set together with avg_power_w, "
                "pulse_energy_j, or peak_power_w."
            )
        if len(explicit_power_fields) > 1:
            raise ValueError(
                "Exactly one pulse normalization input may be explicitly set: one of "
                "avg_power_w, pulse_energy_j, peak_power_w, amplitude."
            )
        if explicit_power_fields == {"amplitude"}:
            warnings.warn(
                "PulseSpec.amplitude is deprecated; use peak_power_w or avg_power_w instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        explicit_width_fields = {"width_fs", "intensity_autocorr_fwhm_fs"} & explicitly_set
        if len(explicit_width_fields) > 1:
            raise ValueError(
                "Only one pulse width input may be explicitly set: width_fs or "
                "intensity_autocorr_fwhm_fs."
            )
        return self


class BeamSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    radius_mm: float = 1.0
    m2: float = 1.0


class LaserSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    pulse: PulseSpec = Field(default_factory=PulseSpec)
    beam: BeamSpec = Field(default_factory=BeamSpec)


@dataclass(slots=True)
class PulseState:
    grid: PulseGrid
    field_t: np.ndarray
    field_w: np.ndarray
    intensity_t: np.ndarray
    spectrum_w: np.ndarray


@dataclass(slots=True)
class BeamState:
    radius_mm: float
    m2: float


@dataclass(slots=True)
class LaserState(State):
    pulse: PulseState
    beam: BeamState
    meta: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def deepcopy(self) -> LaserState:
        return copy.deepcopy(self)

    def hashable_repr(self) -> bytes:
        payload = {
            "metrics": self.metrics,
            "grid": self.pulse.grid.model_dump(mode="json"),
            "beam": {"radius_mm": self.beam.radius_mm, "m2": self.beam.m2},
            "field_t": _hash_array(self.pulse.field_t),
            "field_w": _hash_array(self.pulse.field_w),
            "intensity_t": _hash_array(self.pulse.intensity_t),
            "spectrum_w": _hash_array(self.pulse.spectrum_w),
        }
        blob = json.dumps(payload, sort_keys=True, default=str).encode()
        return hashlib.sha256(blob).digest()


class RunProvenance(BaseModel):
    run_id: str
    created_utc: str
    seed: int
    config_hash: str
    policy_hash: str | None = None

    @classmethod
    def from_seed_and_hash(
        cls, *, seed: int, config_hash: str, policy_hash: str | None
    ) -> RunProvenance:
        now = datetime.now(timezone.utc).isoformat()  # noqa: UP017
        run_key = hashlib.sha256(f"{seed}:{config_hash}:{now}".encode()).hexdigest()[:16]
        return cls(
            run_id=f"run-{run_key}",
            created_utc=now,
            seed=seed,
            config_hash=config_hash,
            policy_hash=policy_hash,
        )


def _hash_array(values: np.ndarray) -> str:
    arr = np.ascontiguousarray(values)
    hasher = hashlib.sha256()
    hasher.update(str(arr.dtype).encode())
    hasher.update(str(arr.shape).encode())
    hasher.update(arr.data)
    return hasher.hexdigest()
