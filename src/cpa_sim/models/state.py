from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    amplitude: float = 1.0
    width_fs: float = Field(
        default=100.0,
        description="Intensity full width at half maximum (FWHM) in femtoseconds.",
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
