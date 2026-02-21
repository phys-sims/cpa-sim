from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml  # type: ignore[import-untyped]

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cpa-sim", description="Run a CPA simulation pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a pipeline configuration")
    run_parser.add_argument("config", type=Path, help="Path to YAML pipeline config")
    run_parser.add_argument("--out", type=Path, required=True, help="Output directory")
    run_parser.add_argument(
        "--dump-state-npz",
        action="store_true",
        help="Write final state arrays to out/state_final.npz.",
    )

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


def _canonical_metrics_payload(result_metrics: dict[str, float]) -> dict[str, Any]:
    return {
        "schema_version": "cpa.metrics.v1",
        "overall": result_metrics,
        "per_stage": _build_stage_metrics(result_metrics),
    }


def _write_state_dump(path: Path, *, state: Any) -> None:
    pulse = state.pulse
    np.savez_compressed(
        path,
        t=np.asarray(pulse.grid.t, dtype=float),
        w=np.asarray(pulse.grid.w, dtype=float),
        field_t_real=np.asarray(np.real(pulse.field_t), dtype=float),
        field_t_imag=np.asarray(np.imag(pulse.field_t), dtype=float),
        field_w_real=np.asarray(np.real(pulse.field_w), dtype=float),
        field_w_imag=np.asarray(np.imag(pulse.field_w), dtype=float),
        intensity_t=np.asarray(pulse.intensity_t, dtype=float),
        spectrum_w=np.asarray(pulse.spectrum_w, dtype=float),
        meta_json=json.dumps(state.meta, sort_keys=True),
        metrics_json=json.dumps(state.metrics, sort_keys=True),
        artifacts_json=json.dumps(state.artifacts, sort_keys=True),
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command != "run":
        return 2

    cfg = _load_config(args.config)
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    stage_plot_dir = out_dir / "stage_plots"
    policy = {
        "cpa.emit_stage_plots": True,
        "cpa.stage_plot_dir": str(stage_plot_dir),
    }

    result = run_pipeline(cfg, policy=policy)

    _write_json(out_dir / "metrics.json", _canonical_metrics_payload(result.metrics))

    artifacts = {**result.artifacts, **result.state.artifacts}
    state_dump_path = out_dir / "state_final.npz"
    if args.dump_state_npz:
        _write_state_dump(state_dump_path, state=result.state)
        artifacts["run.state_dump_npz"] = str(state_dump_path)

    _write_json(
        out_dir / "artifacts.json",
        {
            "schema_version": "cpa.artifacts.v1",
            "paths": artifacts,
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
