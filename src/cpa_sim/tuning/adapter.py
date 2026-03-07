from __future__ import annotations

from typing import Any

DEFAULT_TUNING_POLICY: dict[str, Any] = {
    "cpa.emit_stage_plots": False,
}


def build_tuning_pipeline_policy(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build deterministic tuning run policy with plots disabled by default."""

    return {
        **DEFAULT_TUNING_POLICY,
        **(overrides or {}),
    }
