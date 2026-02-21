from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PipelineConfig
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


@pytest.fixture
def empty_state() -> LaserState:
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


def _fwhm(axis: np.ndarray, values: np.ndarray) -> float:
    peak = float(np.max(values))
    half = 0.5 * peak
    above = np.flatnonzero(values >= half)
    if above.size < 2:
        return 0.0

    left_idx = int(above[0])
    right_idx = int(above[-1])

    if left_idx == 0:
        left = float(axis[left_idx])
    else:
        x0, x1 = float(axis[left_idx - 1]), float(axis[left_idx])
        y0, y1 = float(values[left_idx - 1]), float(values[left_idx])
        left = x0 + (half - y0) * (x1 - x0) / (y1 - y0)

    if right_idx == values.size - 1:
        right = float(axis[right_idx])
    else:
        x0, x1 = float(axis[right_idx]), float(axis[right_idx + 1])
        y0, y1 = float(values[right_idx]), float(values[right_idx + 1])
        right = x0 + (half - y0) * (x1 - x0) / (y1 - y0)

    return right - left


@pytest.mark.physics
@pytest.mark.parametrize(
    ("shape", "expected_tbp"),
    [
        ("gaussian", 0.4412712),
        ("sech2", 0.315),
    ],
)
def test_analytic_laser_fwhm_and_tbp_match_transform_limited_targets(
    empty_state: LaserState,
    shape: str,
    expected_tbp: float,
) -> None:
    # Per-test tolerance block (physics canonical checks).
    tolerances = {
        "fwhm_abs_fs": 0.15,
        "tbp_abs": 0.015,
    }

    target_fwhm_fs = 80.0
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": shape,
                    "width_fs": target_fwhm_fs,
                    "n_samples": 32768,
                    "time_window_fs": 5000.0,
                }
            }
        }
    )
    generated = AnalyticLaserGenStage(cfg.laser_gen).process(empty_state).state

    t_fs = np.asarray(generated.pulse.grid.t, dtype=float)
    intensity = np.asarray(generated.pulse.intensity_t, dtype=float)
    fwhm_t_fs = _fwhm(t_fs, intensity)

    nu_per_fs = np.asarray(generated.pulse.grid.w, dtype=float) / (2.0 * np.pi)
    spectrum = np.asarray(generated.pulse.spectrum_w, dtype=float)
    fwhm_nu_per_fs = _fwhm(nu_per_fs, spectrum)

    tbp = fwhm_t_fs * fwhm_nu_per_fs

    assert fwhm_t_fs == pytest.approx(target_fwhm_fs, abs=tolerances["fwhm_abs_fs"])
    assert tbp == pytest.approx(expected_tbp, abs=tolerances["tbp_abs"])
