from __future__ import annotations

import argparse
from typing import Any

from cpa_sim.tuning.adapter import build_tuning_pipeline_policy


def _parse_bool(value: str) -> bool:
    parsed = value.strip().lower()
    if parsed in {"1", "true", "yes", "y", "on"}:
        return True
    if parsed in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("Expected a boolean value (true/false).")


def add_tune_subcommand(subparsers: Any) -> None:
    tune_parser = subparsers.add_parser("tune", help="Run optimization and fitting workflows")
    tune_subparsers = tune_parser.add_subparsers(dest="tune_command", required=True)

    run_parser = tune_subparsers.add_parser("run", help="Run the generic tuning scaffold")
    run_parser.add_argument("--config", required=True, help="Path to tuning YAML config")
    run_parser.add_argument(
        "--emit-stage-plots",
        type=_parse_bool,
        default=None,
        help="Override stage plot emission for tuning evaluations (default: false).",
    )


def run_tune_command(args: argparse.Namespace) -> int:
    if args.tune_command != "run":
        return 2

    overrides: dict[str, bool] = {}
    if args.emit_stage_plots is not None:
        overrides["cpa.emit_stage_plots"] = args.emit_stage_plots
    policy = build_tuning_pipeline_policy(overrides)

    print(
        "Tune run scaffold initialized. "
        f"Config: {args.config}. "
        f"Policy cpa.emit_stage_plots={policy['cpa.emit_stage_plots']}."
    )
    return 0
