from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.tuning.objectives import (
    build_objective_evaluator,
    exception_to_penalty,
    resolve_metric_path,
    scalar_metric_objective,
    soft_constraint_penalty,
    spectral_correlation_loss,
    spectral_shape_rmse,
    weighted_composite_objective,
)
from cpa_sim.tuning.schema import SoftConstraint, TuningObjective

pytestmark = pytest.mark.unit


def _simple_state() -> LaserState:
    grid = PulseGrid(
        t=[-1.0, 0.0, 1.0],
        w=[-1.0, 0.0, 1.0],
        dt=1.0,
        dw=1.0,
        center_wavelength_nm=1030.0,
    )
    pulse = PulseState(
        grid=grid,
        field_t=np.asarray([0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128),
        field_w=np.asarray([0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128),
        intensity_t=np.asarray([0.0, 1.0, 0.0], dtype=float),
        spectrum_w=np.asarray([0.0, 1.0, 0.0], dtype=float),
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        metrics={},
        artifacts={},
        meta={},
    )


def _write_spectrum_csv(path: Path) -> None:
    path.write_text(
        "omega,signal\n-1.0,0.0\n0.0,1.0\n1.0,0.0\n",
        encoding="utf-8",
    )


def test_resolve_metric_path_supports_exact_and_dotted_paths() -> None:
    flat = {"cpa.metrics.summary.fwhm_fs": 42.0}
    nested = {"cpa": {"metrics": {"summary": {"fwhm_fs": 42.0}}}}

    assert resolve_metric_path(flat, "cpa.metrics.summary.fwhm_fs") == 42.0
    assert resolve_metric_path(nested, "cpa.metrics.summary.fwhm_fs") == 42.0


def test_scalar_metric_objective_target_and_direction_modes() -> None:
    metrics = {"cpa.metrics.summary.fwhm_fs": 40.0}

    assert scalar_metric_objective(metrics, metric_path="cpa.metrics.summary.fwhm_fs") == 40.0
    assert (
        scalar_metric_objective(
            metrics,
            metric_path="cpa.metrics.summary.fwhm_fs",
            direction="maximize",
        )
        == -40.0
    )
    assert (
        scalar_metric_objective(
            metrics,
            metric_path="cpa.metrics.summary.fwhm_fs",
            target_value=35.0,
        )
        == 25.0
    )


def test_spectral_losses_are_zero_for_identical_shapes() -> None:
    axis = np.asarray([-1.0, 0.0, 1.0], dtype=float)
    values = np.asarray([0.0, 1.0, 0.0], dtype=float)

    rmse = spectral_shape_rmse(
        sim_axis=axis,
        sim_values=values,
        target_axis=axis,
        target_values=values,
        normalization="peak",
    )
    corr_loss = spectral_correlation_loss(
        sim_axis=axis,
        sim_values=values,
        target_axis=axis,
        target_values=values,
        normalization="peak",
    )

    assert np.isclose(rmse, 0.0)
    assert np.isclose(corr_loss, 0.0)


def test_weighted_composite_and_soft_constraints_sum_losses() -> None:
    composite = weighted_composite_objective(
        [
            (2.0, 1.5),
            (0.5, lambda: 4.0),
        ]
    )
    assert np.isclose(composite, 5.0)

    metrics = {
        "cpa.metrics.summary.fwhm_fs": 40.0,
        "nested": {"bandwidth": 5.0},
    }
    constraints = [
        SoftConstraint(
            metric="cpa.metrics.summary.fwhm_fs",
            lower=45.0,
            weight=2.0,
            power=2.0,
        ),
        SoftConstraint(metric="nested.bandwidth", upper=4.0, weight=0.5, power=1.0),
    ]
    penalty = soft_constraint_penalty(metrics, constraints)

    # first constraint: (45-40)^2 * 2 = 50
    # second constraint: (5-4)^1 * 0.5 = 0.5
    assert np.isclose(penalty, 50.5)


def test_exception_to_penalty_wraps_errors_and_nonfinite_values() -> None:
    assert exception_to_penalty(lambda: 5.0, penalty=999.0) == 5.0
    assert exception_to_penalty(lambda: float("nan"), penalty=999.0) == 999.0

    def _raise_error() -> float:
        raise RuntimeError("boom")

    assert exception_to_penalty(_raise_error, penalty=123.0) == 123.0


def test_build_objective_evaluator_metric_with_constraints() -> None:
    objective = TuningObjective.model_validate(
        {
            "kind": "metric",
            "metric": "cpa.metrics.summary.fwhm_fs",
            "target_value": 35.0,
            "constraints": [
                {
                    "metric": "cpa.metrics.summary.fwhm_fs",
                    "upper": 37.0,
                    "weight": 2.0,
                    "power": 1.0,
                }
            ],
        }
    )
    evaluator = build_objective_evaluator(objective)

    loss = evaluator({"cpa.metrics.summary.fwhm_fs": 40.0}, _simple_state())

    # target term: (40-35)^2 = 25; penalty: (40-37) * 2 = 6
    assert np.isclose(loss, 31.0)


def test_build_objective_evaluator_spectral_from_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "target.csv"
    _write_spectrum_csv(csv_path)

    objective = TuningObjective.model_validate(
        {
            "kind": "spectral_rmse",
            "target_csv": str(csv_path),
            "target_x_column": "omega",
            "target_y_column": "signal",
            "normalization": "peak",
            "roi": [-1.0, 1.0],
        }
    )
    evaluator = build_objective_evaluator(objective)

    loss = evaluator({}, _simple_state())

    assert np.isclose(loss, 0.0)


def test_build_objective_evaluator_missing_metric_returns_exception_penalty() -> None:
    objective = TuningObjective.model_validate(
        {
            "kind": "metric",
            "metric": "missing.metric",
            "exception_penalty": 321.0,
        }
    )

    evaluator = build_objective_evaluator(objective)
    loss = evaluator({}, _simple_state())

    assert np.isclose(loss, 321.0)
