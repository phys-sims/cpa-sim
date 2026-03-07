from __future__ import annotations

from copy import deepcopy
from typing import Any


def set_dot_path(
    payload: dict[str, Any],
    path: str,
    value: Any,
    *,
    create_missing: bool = False,
) -> dict[str, Any]:
    """Set ``value`` at a dot-separated path in a nested mapping.

    By default, all intermediate path segments must already exist.
    """

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
