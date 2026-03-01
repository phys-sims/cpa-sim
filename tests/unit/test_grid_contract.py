from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.grid_contract import assert_offset_omega_grid
from cpa_sim.models import PipelineConfig
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


def _empty_state() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[-1.0, 1.0], dt=1.0, dw=2.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={}, artifacts={}
    )


@pytest.mark.unit
def test_offset_omega_grid_contract_from_analytic_laser() -> None:
    cfg = PipelineConfig(
        laser_gen={
            "spec": {
                "pulse": {
                    "shape": "gaussian",
                    "n_samples": 4096,
                    "time_window_fs": 2000.0,
                }
            }
        }
    )

    out = AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state
    w = np.asarray(out.pulse.grid.w)
    dw = float(out.pulse.grid.dw)

    assert_offset_omega_grid(w)
    assert abs(float(np.mean(w))) <= 0.5 * abs(dw) + 1e-12
    if w.size % 2 == 0:
        assert np.max(np.abs(w + w[::-1] + dw)) == pytest.approx(0.0, abs=1e-12)
    else:
        assert np.max(np.abs(w + w[::-1])) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.unit
def test_offset_omega_grid_contract_rejects_noncentered_axis() -> None:
    with pytest.raises(ValueError, match="centered near 0"):
        assert_offset_omega_grid(np.array([1.0, 2.0, 3.0]))
