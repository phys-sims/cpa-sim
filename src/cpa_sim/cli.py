from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml  # type: ignore[import-untyped]

from cpa_sim.models import PipelineConfig
from cpa_sim.reporting import (
    build_validation_report,
    render_markdown_report,
    run_pipeline_with_plot_policy,
    write_json,
)
from cpa_sim.tuning.cli import add_tune_subcommand, run_tune_command


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cpa-sim", description="Run and tune CPA simulation pipelines"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a pipeline configuration")
    run_parser.add_argument("config", type=Path, help="Path to YAML pipeline config")
    run_parser.add_argument("--out", type=Path, required=True, help="Output directory")
    run_parser.add_argument(
        "--dump-state-npz",
        action="store_true",
        help="Write final state arrays to out/state_final.npz.",
    )
    run_parser.add_argument(
        "--auto-window",
        action="store_true",
        help="Enable free-space auto-window reruns for configured stages.",
    )
    run_parser.add_argument(
        "--auto-window-stages",
        type=str,
        default="stretcher,compressor",
        help="Comma-separated stage names eligible for auto-window reruns.",
    )
    run_parser.add_argument(
        "--auto-window-print",
        action="store_true",
        help="Print auto-window rerun diagnostics when reruns are triggered.",
    )

    add_tune_subcommand(subparsers)

    return parser.parse_args(argv)


def _load_config(path: Path) -> PipelineConfig:
    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    if not isinstance(payload, dict):
        msg = "Config file root must be a mapping/object."
        raise ValueError(msg)
    return PipelineConfig.model_validate(payload)


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
    if args.command == "tune":
        return run_tune_command(args)

    if args.command != "run":
        return 2

    cfg = _load_config(args.config)
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    policy_overrides: dict[str, Any] = {}
    if args.auto_window:
        stages = [part.strip() for part in args.auto_window_stages.split(",") if part.strip()]
        policy_overrides["cpa.auto_window.enabled"] = True
        policy_overrides["cpa.auto_window.stages"] = stages
        policy_overrides["cpa.auto_window.print"] = bool(args.auto_window_print)

    run_output = run_pipeline_with_plot_policy(
        cfg,
        stage_plot_dir=out_dir / "stage_plots",
        policy_overrides=policy_overrides,
    )
    result = run_output.result
    artifacts = dict(run_output.artifacts)

    write_json(out_dir / "metrics.json", run_output.metrics_payload)

    state_dump_path = out_dir / "state_final.npz"
    if args.dump_state_npz:
        _write_state_dump(state_dump_path, state=result.state)
        artifacts["run.state_dump_npz"] = str(state_dump_path)

    write_json(out_dir / "artifacts.json", run_output.artifacts_payload | {"paths": artifacts})

    report = build_validation_report(cfg=cfg, result=result, artifacts=artifacts)
    write_json(out_dir / "report.json", report.model_dump(mode="json"))
    (out_dir / "report.md").write_text(render_markdown_report(report), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
