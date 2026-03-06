from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpa_sim.models import PipelineConfig
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.pipeline import run_pipeline

DEFAULT_PLOT_POLICY: dict[str, Any] = {
    "cpa.emit_stage_plots": True,
    "cpa.plot.line.threshold_fraction": 1e-3,
    "cpa.plot.line.min_support_width": 0.0,
    "cpa.plot.line.pad_fraction": 0.05,
    "cpa.plot.heatmap.coverage_quantile": 0.999,
    "cpa.plot.heatmap.pad_fraction": 0.10,
    "cpa.plot.heatmap.fallback_behavior": "full_axis",
}


@dataclass(frozen=True)
class CanonicalRunOutput:
    result: StageResult
    policy: dict[str, Any]
    artifacts: dict[str, str]
    metrics_payload: dict[str, Any]
    artifacts_payload: dict[str, Any]


def run_pipeline_with_plot_policy(
    cfg: PipelineConfig,
    *,
    stage_plot_dir: Path,
    policy_overrides: dict[str, Any] | None = None,
) -> CanonicalRunOutput:
    policy = {
        **DEFAULT_PLOT_POLICY,
        "cpa.stage_plot_dir": str(stage_plot_dir),
        **(policy_overrides or {}),
    }
    result = run_pipeline(cfg, policy=policy)
    artifacts = {**result.artifacts, **result.state.artifacts}
    return CanonicalRunOutput(
        result=result,
        policy=policy,
        artifacts=artifacts,
        metrics_payload=canonical_metrics_payload(result.metrics),
        artifacts_payload=canonical_artifacts_payload(artifacts),
    )


def canonical_metrics_payload(result_metrics: dict[str, float]) -> dict[str, Any]:
    return {
        "schema_version": "cpa.metrics.v1",
        "overall": result_metrics,
        "per_stage": _build_stage_metrics(result_metrics),
    }


def canonical_artifacts_payload(artifacts: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "cpa.artifacts.v1",
        "paths": artifacts,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_stage_metrics(metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    stage_metrics: dict[str, dict[str, float]] = {}
    for key, value in metrics.items():
        parts = key.split(".", 3)
        if len(parts) < 4 or parts[0] != "cpa":
            stage_name = "overall"
            metric_name = key
        else:
            stage_name = parts[1]
            metric_name = parts[3]
        stage_metrics.setdefault(stage_name, {})[metric_name] = value
    return stage_metrics
