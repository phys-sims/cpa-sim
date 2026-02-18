from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cpa-sim", description="Run a CPA simulation pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a pipeline configuration")
    run_parser.add_argument("config", type=Path, help="Path to YAML pipeline config")
    run_parser.add_argument("--out", type=Path, required=True, help="Output directory")

    return parser.parse_args(argv)


def _load_config(path: Path) -> PipelineConfig:
    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    if not isinstance(payload, dict):
        msg = "Config file root must be a mapping/object."
        raise ValueError(msg)
    return PipelineConfig.model_validate(payload)


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command != "run":
        return 2

    cfg = _load_config(args.config)
    result = run_pipeline(cfg)

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(out_dir / "metrics_overall.json", result.metrics)
    _write_json(out_dir / "metrics_stages.json", _build_stage_metrics(result.metrics))

    artifacts = {**result.artifacts, **result.state.artifacts}
    _write_json(out_dir / "artifacts_index.json", artifacts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
