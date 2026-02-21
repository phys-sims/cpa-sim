from __future__ import annotations

from cpa_sim.models import BeamSpec, LaserGenCfg, LaserSpec, PulseSpec
from cpa_sim.models.config import recommended_n_samples_for_pulse, validate_pulse_sampling

SHARED_LASER_NAME = "laser_init_case_shared"


def build_shared_laser_gen() -> LaserGenCfg:
    """Return the canonical laser seed used for toy amp case A/B comparisons."""
    width_fs = 2_000.0
    time_window_fs = 120_000.0
    pulse = PulseSpec(
        shape="sech2",
        amplitude=1.0,
        width_fs=width_fs,
        center_wavelength_nm=1560.0,
        rep_rate_mhz=80.0,
        n_samples=recommended_n_samples_for_pulse(
            width_fs=width_fs,
            time_window_fs=time_window_fs,
            min_points_per_fwhm=24,
        ),
        time_window_fs=time_window_fs,
    )
    validate_pulse_sampling(pulse, strict=True)
    return LaserGenCfg(
        name=SHARED_LASER_NAME,
        spec=LaserSpec(
            pulse=pulse,
            beam=BeamSpec(radius_mm=1.0, m2=1.0),
        ),
    )


def shared_laser_spec_summary() -> dict[str, float | str]:
    laser_gen = build_shared_laser_gen()
    pulse = laser_gen.spec.pulse
    return {
        "name": laser_gen.name,
        "shape": pulse.shape,
        "amplitude": pulse.amplitude,
        "width_fs": pulse.width_fs,
        "center_wavelength_nm": pulse.center_wavelength_nm,
        "rep_rate_mhz": pulse.rep_rate_mhz,
        "n_samples": pulse.n_samples,
        "time_window_fs": pulse.time_window_fs,
    }
