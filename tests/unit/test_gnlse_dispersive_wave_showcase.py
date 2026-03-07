from __future__ import annotations

import pytest

from cpa_sim.examples.gnlse_dispersive_wave_showcase import (
    _build_parser,
    build_showcase_case_definitions,
)
from cpa_sim.models import (
    DispersionInterpolationCfg,
    DispersionTaylorCfg,
    FiberCfg,
    WustGnlseNumericsCfg,
)

_EXPECTED_TAYLOR_BETAS_PSN_PER_M = [
    -0.024948815481502,
    8.875391917212998e-05,
    -9.247462376518329e-08,
    1.508210856829677e-10,
]


def _single_fiber_stage(case_index: int = 0, *, case: str = "taylor") -> FiberCfg:
    cases = build_showcase_case_definitions(preset="dispersion", case=case)
    stages = cases[case_index].cfg.stages
    assert stages is not None
    assert len(stages) == 1
    stage = stages[0]
    assert isinstance(stage, FiberCfg)
    return stage


@pytest.mark.unit
def test_dispersion_preset_matches_upstream_pulse_fiber_and_numerics_values() -> None:
    cases = build_showcase_case_definitions(preset="dispersion", case="taylor", seed=7)

    assert len(cases) == 1
    case = cases[0]
    pulse = case.cfg.laser_gen.spec.pulse

    assert case.preset == "dispersion"
    assert case.case == "taylor"
    assert case.stage_name == "fiber_dispersive_wave_taylor"

    assert pulse.shape == "sech2"
    assert pulse.peak_power_w == 10000.0
    assert pulse.width_fs == 50.0
    assert pulse.center_wavelength_nm == 835.0
    assert pulse.n_samples == 16384
    assert pulse.time_window_fs == 12500.0

    stage = _single_fiber_stage(case="taylor")
    physics = stage.physics
    numerics = stage.numerics

    assert physics.length_m == 0.15
    assert physics.loss_db_per_m == 0.0
    assert physics.self_steepening is True
    assert physics.raman is not None
    assert physics.raman.model == "blowwood"

    assert isinstance(numerics, WustGnlseNumericsCfg)
    assert numerics.backend == "wust_gnlse"
    assert numerics.z_saves == 200
    assert numerics.keep_full_solution is True


@pytest.mark.unit
def test_dispersion_preset_taylor_betas_match_upstream_exactly() -> None:
    stage = _single_fiber_stage(case="taylor")
    dispersion = stage.physics.dispersion

    assert isinstance(dispersion, DispersionTaylorCfg)
    assert dispersion.betas_psn_per_m == _EXPECTED_TAYLOR_BETAS_PSN_PER_M


@pytest.mark.unit
def test_dispersion_preset_sets_gamma_to_exactly_zero() -> None:
    stage = _single_fiber_stage(case="taylor")
    assert stage.physics.gamma_1_per_w_m == 0.0


@pytest.mark.unit
def test_dispersion_helper_builds_taylor_and_interpolation_cases() -> None:
    cases = build_showcase_case_definitions(preset="dispersion", case="both", seed=7)

    assert [case.case for case in cases] == ["taylor", "interpolation"]
    assert [case.stage_name for case in cases] == [
        "fiber_dispersive_wave_taylor",
        "fiber_dispersive_wave_interpolation",
    ]


@pytest.mark.unit
def test_dispersion_interpolation_case_uses_interpolation_cfg() -> None:
    stage = _single_fiber_stage(case="interpolation")
    dispersion = stage.physics.dispersion

    assert isinstance(dispersion, DispersionInterpolationCfg)
    assert dispersion.central_wavelength_nm == 835.0
    assert dispersion.lambdas_nm[0] == 400.0
    assert dispersion.lambdas_nm[-1] == 1600.0
    assert len(dispersion.lambdas_nm) == len(dispersion.effective_indices)


@pytest.mark.unit
def test_showcase_cli_parser_supports_dispersion_preset_and_case_flag() -> None:
    parser = _build_parser()

    defaults = parser.parse_args([])
    assert defaults.preset == "dispersion"
    assert defaults.case == "both"

    parsed = parser.parse_args(["--preset", "dispersion", "--case", "interpolation"])
    assert parsed.preset == "dispersion"
    assert parsed.case == "interpolation"
