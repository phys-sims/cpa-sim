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

# Golden values are copied from LaserCalculator.com readouts which are rounded
# for display; use tight but display-aware tolerances.
RTOL_GDD_TOD = 5e-3
ATOL_GDD = 5e3
ATOL_TOD = 1e4
ATOL_ANGLE_DEG = 0.05


def _separation_um(case: dict[str, float | int | str | None]) -> float:
    if case.get("separation_um") is not None:
        return float(case["separation_um"])
    if case.get("separation_mm") is not None:
        return float(case["separation_mm"]) * 1e3
    if case.get("separation_cm") is not None:
        return float(case["separation_cm"]) * 1e4
    if case.get("separation_m") is not None:
        return float(case["separation_m"]) * 1e6
    raise KeyError("Golden case must specify separation_um/mm/cm/m.")


def _expected_with_units(
    case: dict[str, float | int | str | None],
    *,
    ps_key: str,
    conversion: float,
) -> float | None:
    if case.get(ps_key) is None:
        return None

    expected = float(case[ps_key]) * conversion
    expected_assumes_n_passes = float(case.get("expect_assumes_n_passes", 2))
    case_n_passes = float(case["n_passes"])
    return expected * (case_n_passes / expected_assumes_n_passes)


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


def _rms_width_fs(state: LaserState) -> float:
    t_fs = np.asarray(state.pulse.grid.t)
    intensity = np.asarray(state.pulse.intensity_t)
    norm = float(np.sum(intensity))
    if norm <= 0.0:
        return 0.0
    t_mean = float(np.sum(t_fs * intensity) / norm)
    variance = float(np.sum(((t_fs - t_mean) ** 2) * intensity) / norm)
    return float(np.sqrt(max(variance, 0.0)))


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
                separation_um=_separation_um(case),
                wavelength_nm=case["wavelength_nm"],
                diffraction_order=case["diffraction_order"],
                n_passes=case["n_passes"],
                apply_to_pulse=False,
            )
        )
        metrics = stage.process(state).metrics
        expected_gdd_fs2 = _expected_with_units(
            case,
            ps_key="expect_gdd_ps2",
            conversion=1e6,
        )
        if expected_gdd_fs2 is not None:
            assert metrics["golden.gdd_fs2"] == pytest.approx(
                expected_gdd_fs2,
                rel=RTOL_GDD_TOD,
                abs=ATOL_GDD,
            )
        expected_tod_fs3 = _expected_with_units(
            case,
            ps_key="expect_tod_ps3",
            conversion=1e9,
        )
        if expected_tod_fs3 is not None:
            assert metrics["golden.tod_fs3"] == pytest.approx(
                expected_tod_fs3,
                rel=RTOL_GDD_TOD,
                abs=ATOL_TOD,
            )
        if case["expect_diffraction_angle_deg"] is not None:
            # LaserCalculator reports diffraction-angle sign opposite to the
            # current internal convention for this geometry (m=-1 in fixture).
            # Compare magnitudes to guard geometry/units while making the sign
            # convention difference explicit in the test itself.
            assert abs(metrics["golden.diffraction_angle_deg"]) == pytest.approx(
                abs(float(case["expect_diffraction_angle_deg"])),
                abs=ATOL_ANGLE_DEG,
            )


@pytest.mark.unit
def test_treacy_can_compress_quadratic_positive_chirp() -> None:
    initial = _generated_laser_state()
    prechirped = (
        TreacyGratingStage(
            PhaseOnlyDispersionCfg(
                name="prechirp", gdd_fs2=50_000.0, tod_fs3=0.0, apply_to_pulse=True
            )
        )
        .process(initial)
        .state
    )

    compressed = (
        TreacyGratingStage(
            TreacyGratingPairCfg(
                name="compressor",
                line_density_lpmm=1200.0,
                incidence_angle_deg=35.0,
                separation_um=20_000.0,
                wavelength_nm=1030.0,
                n_passes=2,
                include_tod=False,
                apply_to_pulse=True,
            )
        )
        .process(prechirped)
        .state
    )

    assert _rms_width_fs(compressed) < (_rms_width_fs(prechirped) - 5.0)


@pytest.mark.unit
def test_treacy_apply_to_pulse_preserves_energy() -> None:
    initial = _generated_laser_state()
    out = (
        TreacyGratingStage(
            TreacyGratingPairCfg(name="compressor", apply_to_pulse=True, separation_um=100_000.0)
        )
        .process(initial)
        .state
    )

    assert np.sum(out.pulse.intensity_t) * out.pulse.grid.dt == pytest.approx(
        np.sum(initial.pulse.intensity_t) * initial.pulse.grid.dt
    )
