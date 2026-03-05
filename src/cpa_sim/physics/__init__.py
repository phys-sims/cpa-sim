"""Physics utility helpers shared across CPA stages."""

from cpa_sim.physics.pulse_resolve import (
    peak_power_w_from_energy_j,
    rep_rate_hz,
    resolve_intensity_fwhm_fs,
    resolve_peak_power_w,
    resolve_pulse_energy_j,
)
from cpa_sim.physics.windowing import (
    edge_energy_fraction,
    intensity_rms_width_fs,
    intensity_weighted_mean_fs,
    nyquist_energy_fraction,
    pad_laser_state_time,
    recenter_pulse_inplace,
    recenter_state_by_intensity_centroid,
)

__all__ = [
    "peak_power_w_from_energy_j",
    "rep_rate_hz",
    "resolve_intensity_fwhm_fs",
    "resolve_peak_power_w",
    "resolve_pulse_energy_j",
    "edge_energy_fraction",
    "intensity_rms_width_fs",
    "intensity_weighted_mean_fs",
    "nyquist_energy_fraction",
    "pad_laser_state_time",
    "recenter_pulse_inplace",
    "recenter_state_by_intensity_centroid",
]
