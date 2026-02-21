from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PhaseOnlyDispersionCfg, PipelineConfig, TreacyGratingPairCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.free_space.treacy_grating import TreacyGratingStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


@pytest.fixture
def generated_laser() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    seed_state = LaserState(pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={})
    return AnalyticLaserGenStage(PipelineConfig().laser_gen).process(seed_state).state


def _rms_width_fs(state: LaserState) -> float:
    t_fs = np.asarray(state.pulse.grid.t, dtype=float)
    intensity = np.asarray(state.pulse.intensity_t, dtype=float)
    norm = float(np.sum(intensity))
    mean = float(np.sum(t_fs * intensity) / norm)
    variance = float(np.sum(((t_fs - mean) ** 2) * intensity) / norm)
    return float(np.sqrt(max(variance, 0.0)))


@pytest.mark.physics
def test_treacy_canonical_geometry_pins_gdd_tod_and_chirp_sign_behavior(
    generated_laser: LaserState,
) -> None:
    # Per-test tolerance block (LaserCalculator-rounded canonical case).
    tolerances = {
        "gdd_abs_fs2": 5e3,
        "tod_abs_fs3": 1e4,
        "compression_margin_fs": 20.0,
    }

    canonical_metrics_stage = TreacyGratingPairCfg(
        name="canonical",
        line_density_lpmm=1200.0,
        incidence_angle_deg=35.0,
        separation_um=100_000.0,
        wavelength_nm=1030.0,
        diffraction_order=-1,
        n_passes=2,
        apply_to_pulse=False,
    )

    canonical_metrics = TreacyGratingStage(canonical_metrics_stage).process(generated_laser).metrics
    assert canonical_metrics["canonical.gdd_fs2"] == pytest.approx(
        -1.33e6, abs=tolerances["gdd_abs_fs2"]
    )
    assert canonical_metrics["canonical.tod_fs3"] == pytest.approx(
        5.35e6, abs=tolerances["tod_abs_fs3"]
    )

    prechirped = (
        TreacyGratingStage(
            PhaseOnlyDispersionCfg(
                name="prechirp", gdd_fs2=1.33e6, tod_fs3=0.0, apply_to_pulse=True
            )
        )
        .process(generated_laser)
        .state
    )

    chirp_sign_stage = TreacyGratingPairCfg(
        name="canonical",
        line_density_lpmm=1200.0,
        incidence_angle_deg=35.0,
        separation_um=100_000.0,
        wavelength_nm=1030.0,
        diffraction_order=-1,
        n_passes=2,
        include_tod=False,
        apply_to_pulse=True,
    )
    compressed = TreacyGratingStage(chirp_sign_stage).process(prechirped).state

    assert _rms_width_fs(prechirped) > _rms_width_fs(generated_laser)
    assert _rms_width_fs(compressed) < (
        _rms_width_fs(prechirped) - tolerances["compression_margin_fs"]
    )
