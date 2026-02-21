from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LatentFieldContract(BaseModel):
    """Describes latent simulation arrays and their unit conventions."""

    model_config = ConfigDict(frozen=True)

    field_t: str = Field(
        default="PulseState.field_t",
        description="Complex time-domain envelope reference (sqrt(W)).",
    )
    field_w: str = Field(
        default="PulseState.field_w",
        description="Complex frequency-domain envelope reference (sqrt(W)).",
    )
    time_axis: str = Field(default="PulseGrid.t (fs)")
    angular_frequency_axis: str = Field(default="PulseGrid.w (rad/fs)")
    assumptions: list[str] = Field(
        default_factory=lambda: [
            "Internal unit system is fs/um/rad.",
            "Envelope normalization follows ADR-0001 sqrt(W) convention.",
        ]
    )


class ObservableMeasurement(BaseModel):
    """A measured scalar derived from latent state using an explicit method."""

    model_config = ConfigDict(frozen=True)

    name: Literal["intensity_fwhm", "intensity_autocorrelation_fwhm", "spectral_rms_width"]
    value: float
    unit: str
    method: str
    assumptions: list[str] = Field(default_factory=list)


class ObservableContract(BaseModel):
    """Run-level observable surface separated from latent state."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "cpa.observables.v0.1"
    latent_state: LatentFieldContract = Field(default_factory=LatentFieldContract)
    measurements: list[ObservableMeasurement] = Field(default_factory=list)
