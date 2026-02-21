from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MeasurementType = Literal["intensity_fwhm", "autocorrelation_fwhm"]
PulseShape = Literal["gaussian", "sech2"]

_AUTOCORR_DECONV_FACTORS: dict[PulseShape, float] = {
    "gaussian": math.sqrt(2.0),
    "sech2": 1.543,
}


class LaserPulseWidthMapping(BaseModel):
    """Declared mapping from vendor pulse-width measurements to simulation width."""

    model_config = ConfigDict(frozen=True)

    source_measurement_type: MeasurementType
    source_width_ps: float = Field(gt=0.0)
    assumed_pulse_shape: PulseShape
    deconvolution_factor: float = Field(gt=0.0)
    simulation_width_fs: float = Field(gt=0.0)
    uncertainty_rel: float = Field(ge=0.0)
    lower_bound_fs: float = Field(gt=0.0)
    upper_bound_fs: float = Field(gt=0.0)
    assumptions: list[str] = Field(default_factory=list)


def map_laser_pulse_width_to_sim_width(
    *,
    source_width_ps: float,
    source_measurement_type: MeasurementType,
    assumed_pulse_shape: PulseShape,
    uncertainty_rel: float,
    assumptions: list[str] | None = None,
) -> LaserPulseWidthMapping:
    """Convert a vendor pulse width to intensity FWHM used by ``PulseSpec.width_fs``."""

    if source_width_ps <= 0.0:
        raise ValueError("source_width_ps must be > 0.")
    if uncertainty_rel < 0.0:
        raise ValueError("uncertainty_rel must be >= 0.")

    deconvolution_factor = 1.0
    if source_measurement_type == "autocorrelation_fwhm":
        deconvolution_factor = _AUTOCORR_DECONV_FACTORS[assumed_pulse_shape]

    simulation_width_fs = (source_width_ps / deconvolution_factor) * 1_000.0
    lower_bound_fs = simulation_width_fs * (1.0 - uncertainty_rel)
    upper_bound_fs = simulation_width_fs * (1.0 + uncertainty_rel)

    default_assumptions = [
        "Pulse width in simulation is intensity-domain FWHM.",
        "Autocorrelation pulse widths are deconvolved with pulse-shape-specific factors.",
        "Bounds are symmetric relative uncertainty around mapped simulation width.",
    ]
    return LaserPulseWidthMapping(
        source_measurement_type=source_measurement_type,
        source_width_ps=source_width_ps,
        assumed_pulse_shape=assumed_pulse_shape,
        deconvolution_factor=deconvolution_factor,
        simulation_width_fs=simulation_width_fs,
        uncertainty_rel=uncertainty_rel,
        lower_bound_fs=lower_bound_fs,
        upper_bound_fs=upper_bound_fs,
        assumptions=[*(assumptions or []), *default_assumptions],
    )
