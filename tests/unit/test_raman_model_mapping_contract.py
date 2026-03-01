from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    PipelineConfig,
    RamanCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


@pytest.mark.unit
@pytest.mark.gnlse
def test_hollenbeck_raman_model_maps_to_holltrell_function() -> None:
    pytest.importorskip("gnlse")

    n_samples = 1024
    time_window_fs = 2000.0
    center_wavelength_nm = 835.0

    initial = (
        AnalyticLaserGenStage(
            PipelineConfig(
                laser_gen={
                    "spec": {
                        "pulse": {
                            "shape": "gaussian",
                            "width_fs": 80.0,
                            "peak_power_w": 1.0,
                            "n_samples": n_samples,
                            "time_window_fs": time_window_fs,
                            "center_wavelength_nm": center_wavelength_nm,
                        }
                    }
                }
            ).laser_gen
        )
        .process(_seed_state(center_wavelength_nm=center_wavelength_nm))
        .state
    )

    result = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=1e-4,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.0,
                self_steepening=False,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
                raman=RamanCfg(model="hollenbeck"),
            ),
            numerics=WustGnlseNumericsCfg(
                z_saves=4,
                time_window_override_ps=time_window_fs * 1e-3,
                record_backend_version=False,
            ),
        )
    ).process(initial)

    assert np.isfinite(result.state.metrics["fiber.energy_out_au"])


def _seed_state(*, center_wavelength_nm: float) -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(
            t=[0.0, 1.0],
            w=[0.0, 1.0],
            dt=1.0,
            dw=1.0,
            center_wavelength_nm=center_wavelength_nm,
        ),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={},
        metrics={},
        artifacts={},
    )
