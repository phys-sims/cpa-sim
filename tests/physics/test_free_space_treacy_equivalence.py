from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import PhaseOnlyDispersionCfg, PipelineConfig, TreacyGratingPairCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.free_space.treacy_grating import TreacyGratingStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage


def _seed_laser_state() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
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


def _generated_laser() -> LaserState:
    cfg = PipelineConfig()
    return AnalyticLaserGenStage(cfg.laser_gen).process(_seed_laser_state()).state


def _normalized_correlation(a: np.ndarray, b: np.ndarray) -> float:
    a_centered = a - np.mean(a)
    b_centered = b - np.mean(b)
    denom = float(np.linalg.norm(a_centered) * np.linalg.norm(b_centered))
    if denom == 0.0:
        return 1.0
    return float(np.dot(a_centered, b_centered) / denom)


def _rms_width_fs(state: LaserState) -> float:
    t_fs = np.asarray(state.pulse.grid.t, dtype=np.float64)
    intensity = np.asarray(state.pulse.intensity_t, dtype=np.float64)
    norm = float(np.sum(intensity))
    assert norm > 0.0
    mean = float(np.sum(t_fs * intensity) / norm)
    variance = float(np.sum(((t_fs - mean) ** 2) * intensity) / norm)
    return float(np.sqrt(max(variance, 0.0)))


@pytest.mark.physics
def test_treacy_include_tod_matches_polynomial_phase_operator() -> None:
    initial = _generated_laser()

    treacy_cfg = TreacyGratingPairCfg(
        name="treacy",
        line_density_lpmm=1200.0,
        incidence_angle_deg=35.0,
        separation_um=100_000.0,
        wavelength_nm=1030.0,
        diffraction_order=-1,
        n_passes=2,
        include_tod=True,
        apply_to_pulse=True,
    )

    metrics_only = treacy_cfg.model_copy(update={"apply_to_pulse": False})
    treacy_metrics = TreacyGratingStage(metrics_only).process(initial).metrics
    gdd_fs2 = treacy_metrics["treacy.gdd_fs2"]
    tod_fs3 = treacy_metrics["treacy.tod_fs3"]

    treacy_out = TreacyGratingStage(treacy_cfg).process(initial).state

    poly_cfg = PhaseOnlyDispersionCfg(
        name="poly",
        gdd_fs2=gdd_fs2,
        tod_fs3=tod_fs3,
        apply_to_pulse=True,
    )
    poly_out = TreacyGratingStage(poly_cfg).process(initial).state

    treacy_intensity = np.asarray(treacy_out.pulse.intensity_t, dtype=np.float64)
    poly_intensity = np.asarray(poly_out.pulse.intensity_t, dtype=np.float64)
    corr = _normalized_correlation(treacy_intensity, poly_intensity)

    treacy_mag = np.abs(np.asarray(treacy_out.pulse.field_w, dtype=np.complex128))
    poly_mag = np.abs(np.asarray(poly_out.pulse.field_w, dtype=np.complex128))
    rel_spec_l2 = float(np.linalg.norm(treacy_mag - poly_mag) / np.linalg.norm(poly_mag))

    treacy_rms = _rms_width_fs(treacy_out)
    poly_rms = _rms_width_fs(poly_out)
    rms_rel_diff = abs(treacy_rms - poly_rms) / poly_rms

    # Regression guard: PulseGrid.w is already an offset-frequency grid (Δω). If code
    # incorrectly uses (w - ω0_optical) when TOD is enabled, TOD injects an effective
    # quadratic term and this Treacy-vs-polynomial equivalence fails.
    assert corr > 0.999
    assert rel_spec_l2 < 1e-3
    assert rms_rel_diff < 1e-3
