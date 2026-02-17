from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pytest

from cpa_sim.models import (
    PhaseOnlyDispersionCfg,
    PipelineConfig,
    TreacyGratingPairCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.free_space.treacy_grating import TreacyGratingStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage

RTOL = 1e-10
ATOL_GDD = 1e-6
ATOL_TOD = 1e-3


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


def _generated_laser_state() -> LaserState:
    cfg = PipelineConfig()
    return AnalyticLaserGenStage(cfg.laser_gen).process(_empty_state()).state


@pytest.mark.unit
def test_legacy_freespace_cfg_migrates() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg = PipelineConfig(
            stretcher={"name": "stretcher", "kind": "treacy_grating", "gdd_fs2": 42.0}
        )

    assert cfg.stretcher.kind == "phase_only_dispersion"
    assert cfg.stretcher.gdd_fs2 == pytest.approx(42.0)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


@pytest.mark.unit
def test_unit_conversions() -> None:
    initial = _generated_laser_state()
    stage = TreacyGratingStage(
        TreacyGratingPairCfg(
            name="stretcher",
            line_density_lpmm=1200.0,
            incidence_angle_deg=35.0,
            separation_um=100000.0,
            wavelength_nm=1030.0,
            apply_to_pulse=False,
        )
    )
    metrics = stage.process(initial).metrics
    assert metrics["stretcher.period_um"] == pytest.approx(1000.0 / 1200.0)
    assert metrics["stretcher.wavelength_um"] == pytest.approx(1.03)


@pytest.mark.unit
def test_invalid_order_raises() -> None:
    stage = TreacyGratingStage(
        TreacyGratingPairCfg(
            name="bad",
            line_density_lpmm=1200.0,
            incidence_angle_deg=35.0,
            separation_um=100000.0,
            wavelength_nm=1030.0,
            diffraction_order=-3,
        )
    )
    with pytest.raises(ValueError, match="asin domain"):
        stage.process(_generated_laser_state())


@pytest.mark.unit
def test_sign_sanity() -> None:
    metrics = (
        TreacyGratingStage(TreacyGratingPairCfg(name="stretcher", apply_to_pulse=False))
        .process(_generated_laser_state())
        .metrics
    )
    assert metrics["stretcher.gdd_fs2"] < 0.0


@pytest.mark.unit
def test_phase_only_preserves_spectral_magnitude_and_energy() -> None:
    initial = _generated_laser_state()
    stage = TreacyGratingStage(PhaseOnlyDispersionCfg(name="fs", gdd_fs2=2500.0, tod_fs3=-1000.0))
    out = stage.process(initial).state
    assert np.abs(out.pulse.field_w) == pytest.approx(np.abs(initial.pulse.field_w))
    assert np.sum(out.pulse.intensity_t) * out.pulse.grid.dt == pytest.approx(
        np.sum(initial.pulse.intensity_t) * initial.pulse.grid.dt
    )


@pytest.mark.unit
def test_apply_to_pulse_false_is_noop() -> None:
    initial = _generated_laser_state()
    stage = TreacyGratingStage(
        TreacyGratingPairCfg(name="fs", apply_to_pulse=False, separation_um=80000.0)
    )
    out = stage.process(initial).state
    assert out.pulse.field_w == pytest.approx(initial.pulse.field_w)
    assert out.pulse.field_t == pytest.approx(initial.pulse.field_t)


@pytest.mark.unit
def test_treacy_matches_golden_fixture_when_expectations_present() -> None:
    fixture_path = Path("tests/fixtures/treacy_grating_pair_golden.json")
    cases = json.loads(fixture_path.read_text())

    state = _generated_laser_state()
    for case in cases:
        stage = TreacyGratingStage(
            TreacyGratingPairCfg(
                name="golden",
                line_density_lpmm=case["line_density_lpmm"],
                incidence_angle_deg=case["incidence_angle_deg"],
                separation_um=case["separation_um"],
                wavelength_nm=case["wavelength_nm"],
                diffraction_order=case["diffraction_order"],
                n_passes=case["n_passes"],
                apply_to_pulse=False,
            )
        )
        metrics = stage.process(state).metrics
        if case["expect_gdd_fs2"] is not None:
            assert metrics["golden.gdd_fs2"] == pytest.approx(
                case["expect_gdd_fs2"], rel=RTOL, abs=ATOL_GDD
            )
        if case["expect_tod_fs3"] is not None:
            assert metrics["golden.tod_fs3"] == pytest.approx(
                case["expect_tod_fs3"], rel=RTOL, abs=ATOL_TOD
            )
        if case["expect_diffraction_angle_deg"] is not None:
            assert metrics["golden.diffraction_angle_deg"] == pytest.approx(
                case["expect_diffraction_angle_deg"], rel=RTOL, abs=1e-8
            )
