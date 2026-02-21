from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.stages.metrics.standard import _interpolated_fwhm_fs


def _index_only_fwhm_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    half = 0.5 * float(np.max(intensity))
    above = np.flatnonzero(intensity >= half)
    if above.size < 2:
        return 0.0
    return float(t_fs[int(above[-1])] - t_fs[int(above[0])])


@pytest.mark.unit
def test_interpolated_fwhm_matches_analytic_gaussian() -> None:
    expected_fwhm_fs = 80.0
    t_fs = np.linspace(-400.0, 400.0, 8192)
    intensity = np.exp(-4.0 * np.log(2.0) * (t_fs / expected_fwhm_fs) ** 2)

    measured_fwhm_fs = _interpolated_fwhm_fs(
        t=t_fs, intensity=intensity, peak=float(np.max(intensity))
    )

    assert measured_fwhm_fs == pytest.approx(expected_fwhm_fs, rel=0.0, abs=0.02)


@pytest.mark.unit
def test_interpolated_fwhm_matches_analytic_sech2() -> None:
    t0_fs = 35.0
    expected_fwhm_fs = 2.0 * np.arccosh(np.sqrt(2.0)) * t0_fs
    t_fs = np.linspace(-400.0, 400.0, 8192)
    intensity = (1.0 / np.cosh(t_fs / t0_fs)) ** 2

    measured_fwhm_fs = _interpolated_fwhm_fs(
        t=t_fs, intensity=intensity, peak=float(np.max(intensity))
    )

    assert measured_fwhm_fs == pytest.approx(expected_fwhm_fs, rel=0.0, abs=0.02)


@pytest.mark.unit
def test_interpolated_fwhm_improves_low_resolution_error() -> None:
    expected_fwhm_fs = 80.0
    t_fs = np.linspace(-200.0, 200.0, 17)
    intensity = np.exp(-4.0 * np.log(2.0) * (t_fs / expected_fwhm_fs) ** 2)

    index_only_fwhm_fs = _index_only_fwhm_fs(t_fs=t_fs, intensity=intensity)
    interpolated_fwhm_fs = _interpolated_fwhm_fs(
        t=t_fs,
        intensity=intensity,
        peak=float(np.max(intensity)),
    )

    index_error_fs = abs(index_only_fwhm_fs - expected_fwhm_fs)
    interpolated_error_fs = abs(interpolated_fwhm_fs - expected_fwhm_fs)

    assert interpolated_error_fs < index_error_fs
    assert interpolated_error_fs == pytest.approx(0.0, abs=3.0)
