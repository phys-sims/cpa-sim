from __future__ import annotations

import inspect
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline
from cpa_sim.tuning.parameter_space import apply_parameter_values
from cpa_sim.tuning.schema import TuneConfig

DEFAULT_TUNING_POLICY: dict[str, Any] = {
    "cpa.emit_stage_plots": False,
}


def build_tuning_pipeline_policy(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build deterministic tuning run policy with plots disabled by default."""

    return {
        **DEFAULT_TUNING_POLICY,
        **(overrides or {}),
    }


class PipelineTuningAdapter:
    """Thin adapter that evaluates tuned parameter sets against the CPA pipeline."""

    def __init__(self, config: TuneConfig):
        self._config = config
        self._base_payload = _load_base_pipeline_payload(config.base_pipeline_config)

    @property
    def base_payload(self) -> dict[str, Any]:
        return dict(self._base_payload)

    def evaluate(self, values: dict[str, float], *, seed: int | None = None) -> Any:
        effective_seed = self._config.execution.seed if seed is None else seed

        patched = apply_parameter_values(self._base_payload, values)
        runtime_payload = dict(patched.get("runtime", {}))
        runtime_payload["seed"] = effective_seed
        patched["runtime"] = runtime_payload

        cfg = PipelineConfig.model_validate(patched)
        policy = build_tuning_pipeline_policy(self._config.execution.policy_overrides)
        policy["cpa.emit_stage_plots"] = self._config.execution.emit_stage_plots

        result = run_pipeline(cfg, policy=policy)

        objective_value = _compute_objective(
            metrics=result.metrics,
            metric_key=self._config.objective.metric,
            direction=self._config.objective.direction,
        )

        return _build_eval_result(
            parameters=values,
            objective=objective_value,
            metrics=result.metrics,
            artifacts={**result.artifacts, **result.state.artifacts},
            seed=effective_seed,
        )


def _compute_objective(*, metrics: dict[str, float], metric_key: str, direction: str) -> float:
    if metric_key not in metrics:
        raise ValueError(f"Objective metric '{metric_key}' was not produced by run_pipeline.")
    value = float(metrics[metric_key])
    return -value if direction == "maximize" else value


def _build_eval_result(
    *,
    parameters: dict[str, float],
    objective: float,
    metrics: dict[str, float],
    artifacts: dict[str, str],
    seed: int,
) -> Any:
    try:
        ml_module = import_module("phys_sims_utils.ml")
        EvalResult = getattr(ml_module, "EvalResult")
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Tuning requires optional dependency 'phys-sims-utils[ml]'. "
            "Install with `pip install -e .[ml]` or `pip install phys-sims-utils[ml]`."
        ) from exc

    kwargs = {
        "parameters": parameters,
        "parameter_values": parameters,
        "x": parameters,
        "objective": objective,
        "score": objective,
        "loss": objective,
        "metrics": metrics,
        "artifacts": artifacts,
        "metadata": {"seed": seed},
        "success": True,
    }

    signature = inspect.signature(EvalResult)
    accepted = set(signature.parameters)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        filtered = kwargs
    else:
        filtered = {k: v for k, v in kwargs.items() if k in accepted}

    try:
        return EvalResult(**filtered)
    except TypeError as exc:
        raise TypeError("Unable to construct phys_sims_utils.ml.EvalResult.") from exc


def _load_base_pipeline_payload(config: Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(config, dict):
        return dict(config)

    with config.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}

    if not isinstance(payload, dict):
        raise ValueError("Base pipeline config root must be a mapping/object.")
    return payload
