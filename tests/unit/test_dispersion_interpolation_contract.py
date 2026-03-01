from __future__ import annotations

import math

import numpy as np
import pytest

from cpa_sim.models import (
    DispersionInterpolationCfg,
    FiberCfg,
    FiberPhysicsCfg,
    PipelineConfig,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


@pytest.mark.unit
@pytest.mark.gnlse
def test_dispersion_interpolation_contract_matches_direct_gnlse_propagation() -> None:
    gnlse = pytest.importorskip("gnlse")

    if not hasattr(np, "math"):
        np.math = math  # type: ignore[attr-defined]

    lambdas_nm = np.linspace(700.0, 1000.0, 50)
    neff = 1.45 + 1e-4 * (lambdas_nm - 835.0) + 1e-7 * (lambdas_nm - 835.0) ** 2
    central_wavelength_nm = 835.0

    n_samples = 1024
    time_window_fs = 2000.0
    time_window_ps = time_window_fs * 1e-3

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
                            "center_wavelength_nm": central_wavelength_nm,
                        }
                    }
                }
            ).laser_gen
        )
        .process(_seed_state(center_wavelength_nm=central_wavelength_nm))
        .state
    )

    cpa_result = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=1e-4,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.0,
                self_steepening=False,
                dispersion=DispersionInterpolationCfg(
                    effective_indices=neff.tolist(),
                    lambdas_nm=lambdas_nm.tolist(),
                    central_wavelength_nm=central_wavelength_nm,
                ),
            ),
            numerics=WustGnlseNumericsCfg(
                z_saves=5,
                time_window_override_ps=time_window_ps,
                record_backend_version=False,
            ),
        )
    ).process(initial)

    setup = gnlse.GNLSESetup()
    setup.resolution = n_samples
    setup.time_window = time_window_ps
    setup.wavelength = central_wavelength_nm
    setup.fiber_length = 1e-4
    setup.nonlinearity = 0.0
    setup.pulse_model = np.asarray(initial.pulse.field_t, dtype=np.complex128)
    setup.z_saves = 5
    setup.self_steepening = False
    setup.dispersion_model = gnlse.DispersionFiberFromInterpolation(
        0.0,
        neff,
        lambdas_nm,
        central_wavelength_nm,
    )

    solver = gnlse.GNLSE(setup)
    solution = solver.run()
    at = np.asarray(solution.At)
    ref_final = np.asarray(at[-1], dtype=np.complex128) if at.ndim > 1 else at.astype(np.complex128)

    cpa_final = np.asarray(cpa_result.state.pulse.field_t, dtype=np.complex128)
    denom = float(np.linalg.norm(ref_final))
    assert denom > 0.0, "Reference field norm must be positive for a stable contract comparison."

    err = float(np.linalg.norm(cpa_final - ref_final) / denom)
    assert err < 1e-3, (
        "Dispersion interpolation adapter contract mismatch: "
        f"relative L2 error={err:.6e}. "
        "This usually indicates incorrect argument order or units mismatch when mapping "
        "DispersionInterpolationCfg into gnlse.DispersionFiberFromInterpolation."
    )


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
