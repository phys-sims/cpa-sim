from __future__ import annotations

from pathlib import Path
from typing import Any

from cpa_sim.models import PipelineConfig
from cpa_sim.reporting import CanonicalRunOutput, run_pipeline_with_plot_policy, write_json


def ensure_out_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_example_with_default_policy(
    cfg: PipelineConfig,
    *,
    stage_plot_dir: Path,
    policy_overrides: dict[str, Any] | None = None,
) -> CanonicalRunOutput:
    plot_dir = ensure_out_dir(stage_plot_dir)
    return run_pipeline_with_plot_policy(
        cfg,
        stage_plot_dir=plot_dir,
        policy_overrides=policy_overrides,
    )


def write_example_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_out_dir(path.parent)
    write_json(path, payload)


def print_example_artifacts(*, title: str, artifacts: dict[str, Path]) -> None:
    print(title)
    for key, artifact_path in artifacts.items():
        print(f"  {key}: {artifact_path}")
