from __future__ import annotations

from typing import Any


def placeholder_objective(metrics: dict[str, float], _: dict[str, Any] | None = None) -> float:
    """Temporary no-op objective used by the tuning scaffold."""

    if "cpa.metrics.summary.energy_au" in metrics:
        return float(metrics["cpa.metrics.summary.energy_au"])
    return 0.0
