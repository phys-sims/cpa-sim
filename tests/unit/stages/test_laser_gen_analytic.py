from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PipelineConfig
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.physics import peak_power_w_from_energy_j
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


def _empty_state() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={}, artifacts={}
    )


def _fwhm_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    peak = float(np.max(intensity))
    half = 0.5 * peak
    above = np.flatnonzero(intensity >= half)
    if above.size < 2:
        return 0.0

    left_idx = int(above[0])
    right_idx = int(above[-1])

    if left_idx == 0:
        left = float(t_fs[left_idx])
    else:
        x0, x1 = float(t_fs[left_idx - 1]), float(t_fs[left_idx])
        y0, y1 = float(intensity[left_idx - 1]), float(intensity[left_idx])
        left = x0 + (half - y0) * (x1 - x0) / (y1 - y0)

    if right_idx == intensity.size - 1:
        right = float(t_fs[right_idx])
    else:
        x0, x1 = float(t_fs[right_idx]), float(t_fs[right_idx + 1])
        y0, y1 = float(intensity[right_idx]), float(intensity[right_idx + 1])
        right = x0 + (half - y0) * (x1 - x0) / (y1 - y0)

    return right - left


@pytest.mark.unit
@pytest.mark.parametrize("shape", ["gaussian", "sech2"])
def test_analytic_laser_shape_uses_intensity_fwhm(shape: str) -> None:
    expected_fwhm_fs = 80.0
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": shape,
                    "width_fs": expected_fwhm_fs,
                    "n_samples": 16384,
                    "time_window_fs": 3000.0,
                }
            }
        }
    )
    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state

    t_fs = np.asarray(out.pulse.grid.t)
    intensity = np.asarray(out.pulse.intensity_t)
    measured_fwhm_fs = _fwhm_fs(t_fs, intensity)

    assert measured_fwhm_fs == pytest.approx(expected_fwhm_fs, rel=0.0, abs=0.1)


@pytest.mark.unit
def test_analytic_laser_avg_power_resolves_pulse_energy() -> None:
    avg_power_w = 0.42
    rep_rate_mhz = 1.5
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": "gaussian",
                    "avg_power_w": avg_power_w,
                    "rep_rate_mhz": rep_rate_mhz,
                    "width_fs": 120.0,
                    "n_samples": 16384,
                    "time_window_fs": 8000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    dt_fs = out.pulse.grid.dt
    integrated_energy_j = float(np.sum(out.pulse.intensity_t) * dt_fs * 1e-15)
    expected_energy_j = avg_power_w / (rep_rate_mhz * 1e6)

    assert integrated_energy_j == pytest.approx(expected_energy_j, rel=5e-4)
    assert out.meta["laser.pulse_energy_j"] == pytest.approx(expected_energy_j, rel=5e-4)
    assert out.metrics["laser.pulse_energy_j"] == pytest.approx(expected_energy_j, rel=5e-4)
    assert out.meta["laser.avg_power_w"] == pytest.approx(avg_power_w, rel=5e-4)


@pytest.mark.unit
@pytest.mark.parametrize("shape", ["gaussian", "sech2"])
def test_analytic_laser_peak_power_matches_expected_from_avg_power(shape: str) -> None:
    avg_power_w = 0.75
    rep_rate_mhz = 2.0
    width_fs = 90.0
    expected_pulse_energy_j = avg_power_w / (rep_rate_mhz * 1e6)
    expected_peak_power_w = peak_power_w_from_energy_j(
        energy_j=expected_pulse_energy_j,
        width_fs=width_fs,
        shape=shape,
    )
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": shape,
                    "avg_power_w": avg_power_w,
                    "rep_rate_mhz": rep_rate_mhz,
                    "width_fs": width_fs,
                    "n_samples": 32768,
                    "time_window_fs": 9000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    measured_peak_power_w = float(np.max(out.pulse.intensity_t))

    assert measured_peak_power_w == pytest.approx(expected_peak_power_w, rel=2e-4)
    assert out.meta["laser.peak_power_w"] == pytest.approx(expected_peak_power_w, rel=2e-4)
    assert out.metrics["laser.peak_power_w"] == pytest.approx(expected_peak_power_w, rel=2e-4)


@pytest.mark.unit
def test_analytic_laser_autocorr_width_is_deconvolved_and_audited() -> None:
    intensity_fwhm_fs = 100.0
    autocorr_fwhm_fs = intensity_fwhm_fs / 0.648
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": "sech2",
                    "intensity_autocorr_fwhm_fs": autocorr_fwhm_fs,
                    "n_samples": 16384,
                    "time_window_fs": 5000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    t_fs = np.asarray(out.pulse.grid.t)
    measured_fwhm_fs = _fwhm_fs(t_fs, np.asarray(out.pulse.intensity_t))

    assert measured_fwhm_fs == pytest.approx(intensity_fwhm_fs, rel=0.0, abs=0.2)
    assert out.meta["laser.intensity_fwhm_fs"] == pytest.approx(intensity_fwhm_fs, rel=0.0, abs=0.2)
    assert out.meta["laser.intensity_autocorr_fwhm_fs_input"] == pytest.approx(autocorr_fwhm_fs)


@pytest.mark.unit
def test_analytic_laser_gaussian_avg_power_case_matches_energy_and_peak_targets() -> None:
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": "gaussian",
                    "avg_power_w": 0.3,
                    "rep_rate_mhz": 1_155.0,
                    "width_fs": 7_200.0,
                    "n_samples": 16384,
                    "time_window_fs": 80_000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    dt_s = float(out.pulse.grid.dt) * 1e-15
    energy_j = float(np.sum(np.abs(out.pulse.field_t) ** 2) * dt_s)
    expected_energy_j = 0.3 / (1_155.0 * 1e6)

    assert energy_j == pytest.approx(expected_energy_j, rel=1e-3)
    assert float(np.max(np.abs(out.pulse.field_t) ** 2)) == pytest.approx(33.8902337193, rel=5e-3)


@pytest.mark.unit
def test_analytic_laser_sech2_autocorr_case_deconvolves_to_expected_intensity_fwhm() -> None:
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": "sech2",
                    "intensity_autocorr_fwhm_fs": 11_111.111111,
                    "n_samples": 16384,
                    "time_window_fs": 80_000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    t_fs = np.asarray(out.pulse.grid.t)
    measured_fwhm_fs = _fwhm_fs(t_fs, np.asarray(out.pulse.intensity_t))

    assert measured_fwhm_fs == pytest.approx(7_200.0, rel=0.0, abs=1.0)
