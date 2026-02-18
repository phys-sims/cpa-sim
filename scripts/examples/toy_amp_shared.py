from __future__ import annotations

from cpa_sim.models import BeamSpec, LaserGenCfg, LaserSpec, PulseSpec

SHARED_LASER_NAME = "laser_init_case_shared"


def build_shared_laser_gen() -> LaserGenCfg:
    """Return the canonical laser seed used for toy amp case A/B comparisons."""
    return LaserGenCfg(
        name=SHARED_LASER_NAME,
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="sech2",
                amplitude=1.0,
                width_fs=2_000.0,
                center_wavelength_nm=1560.0,
                n_samples=512,
                time_window_fs=120_000.0,
            ),
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
        "n_samples": pulse.n_samples,
        "time_window_fs": pulse.time_window_fs,
    }
