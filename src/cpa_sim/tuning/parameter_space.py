from __future__ import annotations

from copy import deepcopy
from typing import Any


def set_dot_path(payload: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Set ``value`` at a dot-separated path in a nested mapping."""

    if not path:
        raise ValueError("Dot path must be non-empty.")

    parts = path.split(".")
    cursor: dict[str, Any] = payload
    for key in parts[:-1]:
        next_value = cursor.get(key)
        if next_value is None:
            next_value = {}
            cursor[key] = next_value
        if not isinstance(next_value, dict):
            raise ValueError(f"Path segment '{key}' is not a mapping in '{path}'.")
        cursor = next_value

    cursor[parts[-1]] = value
    return payload


def apply_parameter_values(
    base_config: dict[str, Any], parameter_values: dict[str, Any]
) -> dict[str, Any]:
    """Return a patched copy of ``base_config`` with parameter values applied."""

    patched = deepcopy(base_config)
    for path, value in parameter_values.items():
        set_dot_path(patched, path, value)
    return patched
