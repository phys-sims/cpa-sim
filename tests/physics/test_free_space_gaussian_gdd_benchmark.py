from __future__ import annotations

import math

import numpy as np
import pytest

from cpa_sim.models import PhaseOnlyDispersionCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.free_space.treacy_grating import TreacyGratingStage


def _gaussian_envelope_state(
    *, tau0_fs: float, time_window_fs: float, n_samples: int
) -> LaserState:
    t_fs = np.linspace(-0.5 * time_window_fs, 0.5 * time_window_fs, n_samples)
    dt_fs = float(t_fs[1] - t_fs[0])

    # Field-envelope benchmark pulse:
    # E(t) = exp(-t^2 / (2 tau0^2))
    field_t = np.exp(-(t_fs**2) / (2.0 * tau0_fs**2)).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    w_rad_per_fs = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t_fs.size, d=dt_fs))
    dw_rad_per_fs = float(w_rad_per_fs[1] - w_rad_per_fs[0])

    pulse = PulseState(
        grid=PulseGrid(
            t=t_fs.tolist(),
            w=w_rad_per_fs.tolist(),
            dt=dt_fs,
            dw=dw_rad_per_fs,
            center_wavelength_nm=1030.0,
        ),
        field_t=field_t,
        field_w=field_w,
        intensity_t=np.abs(field_t) ** 2,
        spectrum_w=np.abs(field_w) ** 2,
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={},
        metrics={},
        artifacts={},
    )


def _intensity_rms_width_fs(state: LaserState) -> float:
    t_fs = np.asarray(state.pulse.grid.t, dtype=np.float64)
    intensity = np.asarray(state.pulse.intensity_t, dtype=np.float64)
    norm = float(np.sum(intensity))
    mean_fs = float(np.sum(t_fs * intensity) / norm)
    variance_fs2 = float(np.sum(((t_fs - mean_fs) ** 2) * intensity) / norm)
    return float(np.sqrt(max(variance_fs2, 0.0)))


@pytest.mark.physics
def test_phase_only_dispersion_matches_gaussian_gdd_analytic_broadening() -> None:
    tau0_fs = 80.0
    sigma0_fs = tau0_fs / math.sqrt(2.0)

    initial = _gaussian_envelope_state(
        tau0_fs=tau0_fs,
        time_window_fs=50_000.0,
        n_samples=32_768,
    )

    gdd_values_fs2 = [0.0, 1.0e5, -1.0e5, 2.0e5]
    observed_sigmas: dict[float, float] = {}

    for gdd_fs2 in gdd_values_fs2:
        out = (
            TreacyGratingStage(
                PhaseOnlyDispersionCfg(
                    name=f"phase_{int(gdd_fs2)}",
                    gdd_fs2=gdd_fs2,
                    tod_fs3=0.0,
                    apply_to_pulse=True,
                )
            )
            .process(initial)
            .state
        )

        sigma_out_fs = _intensity_rms_width_fs(out)
        sigma_expected_fs = sigma0_fs * math.sqrt(1.0 + (gdd_fs2 / tau0_fs**2) ** 2)

        observed_sigmas[gdd_fs2] = sigma_out_fs
        assert sigma_out_fs == pytest.approx(sigma_expected_fs, rel=1e-2)

    # Broadening magnitude should depend on |GDD|, not sign.
    assert observed_sigmas[1.0e5] == pytest.approx(observed_sigmas[-1.0e5], rel=1e-3)

    # Anti-aliasing sanity check for the largest |GDD| case.
    time_window_fs = float(initial.pulse.grid.t[-1] - initial.pulse.grid.t[0])
    assert observed_sigmas[2.0e5] < (time_window_fs / 10.0)
