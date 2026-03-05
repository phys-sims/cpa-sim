from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal


HeatmapFallback = Literal["full_axis", "line_window"]


@dataclass(frozen=True)
class LineWindowPolicy:
    threshold_fraction: float = 1e-3
    min_support_width: float = 0.0
    pad_fraction: float = 0.05


@dataclass(frozen=True)
class HeatmapWindowPolicy:
    coverage_quantile: float = 0.999
    pad_fraction: float = 0.10
    fallback_behavior: HeatmapFallback = "full_axis"


@dataclass(frozen=True)
class PlotWindowPolicy:
    line: LineWindowPolicy = LineWindowPolicy()
    heatmap: HeatmapWindowPolicy = HeatmapWindowPolicy()

    @classmethod
    def from_policy_bag(cls, policy: Any) -> PlotWindowPolicy:
        if policy is None:
            return cls()

        line = LineWindowPolicy(
            threshold_fraction=float(_policy_get(policy, "cpa.plot.line.threshold_fraction", 1e-3)),
            min_support_width=float(_policy_get(policy, "cpa.plot.line.min_support_width", 0.0)),
            pad_fraction=float(_policy_get(policy, "cpa.plot.line.pad_fraction", 0.05)),
        )
        heatmap = HeatmapWindowPolicy(
            coverage_quantile=float(
                _policy_get(policy, "cpa.plot.heatmap.coverage_quantile", 0.999)
            ),
            pad_fraction=float(_policy_get(policy, "cpa.plot.heatmap.pad_fraction", 0.10)),
            fallback_behavior=_coerce_fallback(
                _policy_get(policy, "cpa.plot.heatmap.fallback_behavior", "full_axis")
            ),
        )
        return cls(line=line, heatmap=heatmap)


def _coerce_fallback(value: Any) -> HeatmapFallback:
    text = str(value)
    if text == "full_axis":
        return "full_axis"
    if text == "line_window":
        return "line_window"
    return "full_axis"


def _policy_get(policy: Any, key: str, default: Any = None) -> Any:
    if policy is None:
        return default
    if isinstance(policy, Mapping):
        return policy.get(key, default)
    getter = getattr(policy, "get", None)
    if callable(getter):
        return getter(key, default)
    return default
