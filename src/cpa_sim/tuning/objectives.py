from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

import numpy as np

from cpa_sim.models.state import LaserState
from cpa_sim.tuning.schema import SoftConstraint, TuningObjective
from cpa_sim.tuning.targets import (
    NormalizationMode,
    TargetTrace,
    interpolate_trace,
    load_target_trace_csv,
    normalize_trace,
    select_roi,
    simulator_trace_for_alignment,
)


def placeholder_objective(metrics: dict[str, float], _: dict[str, Any] | None = None) -> float:
    """Back-compat placeholder entry point mapped to scalar metric objective behavior."""

    return scalar_metric_objective(
        metrics,
        metric_path="cpa.metrics.summary.energy_au",
        direction="minimize",
    )


def build_objective_evaluator(
    objective: TuningObjective,
) -> Callable[[Mapping[str, Any], LaserState], float]:
    target_trace: TargetTrace | None = None
    if objective.kind in {"spectral_rmse", "spectral_correlation"}:
        target_trace = load_target_trace_csv(
            objective.target_csv_path,
            x_column=objective.target_x_column,
            y_column=objective.target_y_column,
            trace_kind=objective.target_trace,
            axis_kind=objective.target_axis,
        )

    def _evaluate(metrics: Mapping[str, Any], state: LaserState) -> float:
        def _compute_raw() -> float:
            base_loss = _base_objective_loss(
                objective=objective,
                metrics=metrics,
                state=state,
                target=target_trace,
            )
            penalty_loss = soft_constraint_penalty(metrics, objective.constraints)
            return weighted_composite_objective(
                [
                    (float(objective.weight), lambda: base_loss),
                    (1.0, lambda: penalty_loss),
                ]
            )

        return exception_to_penalty(_compute_raw, penalty=objective.exception_penalty)

    return _evaluate


def scalar_metric_objective(
    metrics: Mapping[str, Any],
    *,
    metric_path: str,
    target_value: float | None = None,
    direction: Literal["minimize", "maximize"] = "minimize",
) -> float:
    value = resolve_metric_path(metrics, metric_path)
    if target_value is not None:
        delta = value - float(target_value)
        return float(delta * delta)
    return -value if direction == "maximize" else value


def spectral_shape_rmse(
    *,
    sim_axis: np.ndarray,
    sim_values: np.ndarray,
    target_axis: np.ndarray,
    target_values: np.ndarray,
    normalization: NormalizationMode = "peak",
    roi: tuple[float, float] | None = None,
) -> float:
    sim_aligned, target_aligned = _aligned_pair(
        sim_axis=sim_axis,
        sim_values=sim_values,
        target_axis=target_axis,
        target_values=target_values,
        normalization=normalization,
        roi=roi,
    )
    diff = sim_aligned - target_aligned
    return float(np.sqrt(np.mean(diff * diff)))


def spectral_correlation_loss(
    *,
    sim_axis: np.ndarray,
    sim_values: np.ndarray,
    target_axis: np.ndarray,
    target_values: np.ndarray,
    normalization: NormalizationMode = "peak",
    roi: tuple[float, float] | None = None,
) -> float:
    sim_aligned, target_aligned = _aligned_pair(
        sim_axis=sim_axis,
        sim_values=sim_values,
        target_axis=target_axis,
        target_values=target_values,
        normalization=normalization,
        roi=roi,
    )

    sim_centered = sim_aligned - float(np.mean(sim_aligned))
    target_centered = target_aligned - float(np.mean(target_aligned))
    denom = float(np.linalg.norm(sim_centered) * np.linalg.norm(target_centered))
    if denom <= 0.0:
        return 1.0

    corr = float(np.dot(sim_centered, target_centered) / denom)
    corr = float(np.clip(corr, -1.0, 1.0))
    return 1.0 - corr


def weighted_composite_objective(
    terms: Sequence[tuple[float, Callable[[], float] | float]],
) -> float:
    total = 0.0
    for weight, term in terms:
        if weight == 0.0:
            continue
        value = term() if callable(term) else float(term)
        total += float(weight) * float(value)
    return total


def soft_constraint_penalty(
    metrics: Mapping[str, Any],
    constraints: Sequence[SoftConstraint],
) -> float:
    penalty_total = 0.0
    for constraint in constraints:
        metric_value = resolve_metric_path(metrics, constraint.metric)
        lower_violation = (
            max(0.0, float(constraint.lower) - metric_value)
            if constraint.lower is not None
            else 0.0
        )
        upper_violation = (
            max(0.0, metric_value - float(constraint.upper))
            if constraint.upper is not None
            else 0.0
        )
        target_violation = (
            abs(metric_value - float(constraint.target)) if constraint.target is not None else 0.0
        )

        violation = lower_violation + upper_violation + target_violation
        if violation <= 0.0:
            continue
        penalty_total += float(constraint.weight) * float(violation ** float(constraint.power))
    return penalty_total


def resolve_metric_path(metrics: Mapping[str, Any], path: str) -> float:
    if not path.strip():
        raise ValueError("Metric path must be a non-empty string.")

    if path in metrics:
        return _coerce_scalar(metrics[path], path)

    current: Any = metrics
    for segment in path.split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                raise ValueError(f"Metric path '{path}' is missing segment '{segment}'.")
            current = current[segment]
        else:
            if not hasattr(current, segment):
                raise ValueError(f"Metric path '{path}' is missing segment '{segment}'.")
            current = getattr(current, segment)

    return _coerce_scalar(current, path)


def exception_to_penalty(fn: Callable[[], float], *, penalty: float) -> float:
    try:
        value = float(fn())
    except Exception:
        return float(penalty)

    if not np.isfinite(value):
        return float(penalty)
    return value


def _base_objective_loss(
    *,
    objective: TuningObjective,
    metrics: Mapping[str, Any],
    state: LaserState,
    target: TargetTrace | None,
) -> float:
    if objective.kind == "metric":
        metric_path = objective.metric_path
        if metric_path is None:
            raise ValueError("metric objective is missing metric_path")
        return scalar_metric_objective(
            metrics,
            metric_path=metric_path,
            target_value=objective.target_value,
            direction=objective.direction,
        )

    if target is None:
        raise ValueError("Spectral objectives require a preloaded target trace.")

    sim_axis, sim_values = simulator_trace_for_alignment(
        state,
        trace_kind=target.trace_kind,
        axis_kind=target.axis_kind,
    )

    if objective.kind == "spectral_rmse":
        return spectral_shape_rmse(
            sim_axis=sim_axis,
            sim_values=sim_values,
            target_axis=target.axis,
            target_values=target.values,
            normalization=objective.normalization,
            roi=objective.roi,
        )

    if objective.kind == "spectral_correlation":
        return spectral_correlation_loss(
            sim_axis=sim_axis,
            sim_values=sim_values,
            target_axis=target.axis,
            target_values=target.values,
            normalization=objective.normalization,
            roi=objective.roi,
        )

    raise ValueError(f"Unsupported objective kind '{objective.kind}'.")


def _aligned_pair(
    *,
    sim_axis: np.ndarray,
    sim_values: np.ndarray,
    target_axis: np.ndarray,
    target_values: np.ndarray,
    normalization: NormalizationMode,
    roi: tuple[float, float] | None,
) -> tuple[np.ndarray, np.ndarray]:
    sim_axis_f, sim_values_f = select_roi(
        np.asarray(sim_axis, dtype=float),
        np.asarray(sim_values, dtype=float),
        window=roi,
    )
    target_axis_f, target_values_f = select_roi(
        np.asarray(target_axis, dtype=float),
        np.asarray(target_values, dtype=float),
        window=roi,
    )

    target_interp = interpolate_trace(
        source_axis=target_axis_f,
        source_values=target_values_f,
        target_axis=sim_axis_f,
        fill_value=0.0,
    )

    sim_norm = normalize_trace(sim_values_f, axis=sim_axis_f, mode=normalization)
    target_norm = normalize_trace(target_interp, axis=sim_axis_f, mode=normalization)
    return sim_norm, target_norm


def _coerce_scalar(value: Any, path: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Metric path '{path}' resolved to non-scalar value {value!r}.") from exc
