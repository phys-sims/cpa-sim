from __future__ import annotations

import pytest

from cpa_sim.models.state import PulseSpec
from cpa_sim.physics.pulse_resolve import (
    peak_power_w_from_energy_j,
    rep_rate_hz,
    resolve_intensity_fwhm_fs,
    resolve_peak_power_w,
    resolve_pulse_energy_j,
)


@pytest.mark.unit
def test_rep_rate_hz_converts_mhz_to_hz() -> None:
    assert rep_rate_hz(1_155.0) == pytest.approx(1_155_000_000.0)


@pytest.mark.unit
def test_resolve_energy_and_peak_power_gaussian_from_average_power() -> None:
    pulse = PulseSpec(shape="gaussian", avg_power_w=0.3, rep_rate_mhz=1_155.0, width_fs=7_200.0)

    energy_j = resolve_pulse_energy_j(pulse)
    assert energy_j is not None
    assert energy_j == pytest.approx(2.597402597e-10)

    peak_power_w = resolve_peak_power_w(pulse, width_fs=resolve_intensity_fwhm_fs(pulse))
    assert peak_power_w == pytest.approx(33.8902337193)


@pytest.mark.unit
def test_resolve_energy_and_peak_power_sech2_from_average_power() -> None:
    pulse = PulseSpec(shape="sech2", avg_power_w=0.3, rep_rate_mhz=1_155.0, width_fs=7_200.0)

    energy_j = resolve_pulse_energy_j(pulse)
    assert energy_j is not None
    assert energy_j == pytest.approx(2.597402597e-10)

    peak_power_w = resolve_peak_power_w(pulse, width_fs=resolve_intensity_fwhm_fs(pulse))
    assert peak_power_w == pytest.approx(31.7955839473)


@pytest.mark.unit
def test_peak_power_w_from_energy_j_matches_gaussian_numeric_reference() -> None:
    energy_j = 0.3 / (1_155.0 * 1e6)

    peak_power_w = peak_power_w_from_energy_j(
        energy_j=energy_j,
        width_fs=7_200.0,
        shape="gaussian",
    )

    assert peak_power_w == pytest.approx(33.8902337193)


@pytest.mark.unit
def test_peak_power_w_from_energy_j_matches_sech2_numeric_reference() -> None:
    energy_j = 0.3 / (1_155.0 * 1e6)

    peak_power_w = peak_power_w_from_energy_j(
        energy_j=energy_j,
        width_fs=7_200.0,
        shape="sech2",
    )

    assert peak_power_w == pytest.approx(31.7955839473)


@pytest.mark.unit
def test_resolve_intensity_fwhm_fs_deconvolves_sech2_autocorrelation_width() -> None:
    pulse = PulseSpec(shape="sech2", intensity_autocorr_fwhm_fs=11_111.111111)

    resolved = resolve_intensity_fwhm_fs(pulse)
    assert resolved == pytest.approx(7_200.0, rel=1e-6)


@pytest.mark.unit
def test_peak_power_w_from_energy_j_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError, match="Unknown pulse shape"):
        peak_power_w_from_energy_j(energy_j=1e-9, width_fs=120.0, shape="lorentzian")


@pytest.mark.unit
def test_resolve_peak_power_w_uses_legacy_default_amplitude_when_no_power_inputs() -> None:
    pulse = PulseSpec(width_fs=100.0)
    assert resolve_peak_power_w(pulse, width_fs=100.0) == pytest.approx(1.0)


@pytest.mark.unit
def test_resolve_intensity_fwhm_fs_unknown_shape_autocorr_raises_clear_error() -> None:
    class FakePulseSpec:
        shape = "triangle"
        width_fs = 100.0
        intensity_autocorr_fwhm_fs = 200.0
        pulse_energy_j = None
        avg_power_w = None
        peak_power_w = None
        rep_rate_mhz = 1.0
        amplitude = 1.0

    with pytest.raises(ValueError, match="Unknown pulse shape"):
        resolve_intensity_fwhm_fs(FakePulseSpec())
