from __future__ import annotations

import pytest

from cpa_sim.models.config import recommended_n_samples_for_pulse, validate_pulse_sampling
from cpa_sim.models.state import PulseSpec


@pytest.mark.unit
def test_recommended_n_samples_for_pulse_meets_points_per_fwhm_target() -> None:
    n_samples = recommended_n_samples_for_pulse(
        width_fs=2_000.0,
        time_window_fs=120_000.0,
        min_points_per_fwhm=24,
    )
    dt_fs = 120_000.0 / float(n_samples - 1)

    assert n_samples == 2048
    assert dt_fs <= 2_000.0 / 24.0


@pytest.mark.unit
def test_validate_pulse_sampling_raises_when_strict_and_underresolved() -> None:
    pulse = PulseSpec(width_fs=80.0, n_samples=256, time_window_fs=6_000.0)

    with pytest.raises(ValueError, match="dt_fs <= resolved_intensity_fwhm_fs / N_min"):
        validate_pulse_sampling(pulse, min_points_per_fwhm=24, strict=True)


@pytest.mark.unit
def test_validate_pulse_sampling_warns_for_low_nyquist_margin() -> None:
    pulse = PulseSpec(shape="sech2", width_fs=100.0, n_samples=128, time_window_fs=2_000.0)

    with pytest.warns(UserWarning, match="spectral Nyquist margin"):
        validate_pulse_sampling(pulse, min_points_per_fwhm=4, nyquist_margin=12.0, strict=False)


@pytest.mark.unit
def test_validate_pulse_sampling_uses_resolved_intensity_fwhm_from_autocorrelation() -> None:
    pulse = PulseSpec(
        shape="sech2",
        intensity_autocorr_fwhm_fs=154.320987654321,
        n_samples=256,
        time_window_fs=6_000.0,
    )

    with pytest.raises(
        ValueError,
        match=r"resolved_intensity_fwhm_fs=100\.000 fs",
    ):
        validate_pulse_sampling(pulse, min_points_per_fwhm=24, strict=True)
