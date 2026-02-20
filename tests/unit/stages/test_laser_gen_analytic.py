from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PipelineConfig
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
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
