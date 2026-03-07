from __future__ import annotations

import inspect
from copy import deepcopy
from importlib import import_module
from typing import Any

from cpa_sim.tuning.schema import TunableParameter, TuneConfig


def set_dot_path(
    payload: dict[str, Any],
    path: str,
    value: Any,
    *,
    create_missing: bool = False,
) -> dict[str, Any]:
    """Set ``value`` at a dot-separated path in a nested mapping."""

    if not path:
        raise ValueError("Dot path must be non-empty.")

    parts = path.split(".")
    cursor: dict[str, Any] = payload
    for key in parts[:-1]:
        if key not in cursor:
            if create_missing:
                cursor[key] = {}
            else:
                raise ValueError(f"Unknown path segment '{key}' in '{path}'.")

        next_value = cursor[key]
        if not isinstance(next_value, dict):
            raise ValueError(f"Path segment '{key}' is not a mapping in '{path}'.")
        cursor = next_value

    leaf_key = parts[-1]
    if leaf_key not in cursor and not create_missing:
        raise ValueError(f"Unknown target key '{leaf_key}' in '{path}'.")

    cursor[leaf_key] = value
    return payload


def apply_parameter_values(
    base_config: dict[str, Any], parameter_values: dict[str, Any]
) -> dict[str, Any]:
    """Return a patched copy of ``base_config`` with parameter values applied."""

    patched = deepcopy(base_config)
    for path, value in parameter_values.items():
        set_dot_path(patched, path, value)
    return patched


def tuning_to_parameter_space(tune_config: TuneConfig) -> Any:
    """Convert tuning schema to ``phys_sims_utils.ml.ParameterSpace``."""

    try:
        ml_module = import_module("phys_sims_utils.ml")
        Parameter = getattr(ml_module, "Parameter")
        ParameterSpace = getattr(ml_module, "ParameterSpace")
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Tuning requires optional dependency 'phys-sims-utils[ml]'. "
            "Install with `pip install -e .[ml]` or `pip install phys-sims-utils[ml]`."
        ) from exc

    parameters = [_build_parameter(Parameter, parameter) for parameter in tune_config.parameters]
    return _build_parameter_space(ParameterSpace, parameters)


def _build_parameter(parameter_cls: type[Any], parameter: TunableParameter) -> Any:
    lower, upper = parameter.bounds
    attempts: list[dict[str, Any]] = [
        {
            "name": parameter.name,
            "path": parameter.path,
            "lower": lower,
            "upper": upper,
            "transform": parameter.transform,
        },
        {
            "name": parameter.name,
            "path": parameter.path,
            "bounds": parameter.bounds,
            "transform": parameter.transform,
        },
        {
            "name": parameter.name,
            "bounds": parameter.bounds,
            "metadata": {"path": parameter.path},
            "transform": parameter.transform,
        },
    ]

    for kwargs in attempts:
        filtered = _filtered_kwargs(parameter_cls, kwargs)
        try:
            return parameter_cls(**filtered)
        except TypeError:
            continue

    raise TypeError("Unable to instantiate phys_sims_utils.ml.Parameter with supported signatures.")


def _build_parameter_space(space_cls: type[Any], parameters: list[Any]) -> Any:
    attempts: list[dict[str, Any]] = [{"parameters": parameters}, {"params": parameters}]
    for kwargs in attempts:
        filtered = _filtered_kwargs(space_cls, kwargs)
        try:
            return space_cls(**filtered)
        except TypeError:
            continue
    return space_cls(parameters)


def _filtered_kwargs(target: type[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(target)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        return {k: v for k, v in kwargs.items() if v is not None}
    accepted = set(signature.parameters)
    return {k: v for k, v in kwargs.items() if k in accepted and v is not None}
