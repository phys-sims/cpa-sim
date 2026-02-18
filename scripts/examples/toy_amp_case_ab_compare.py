from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from toy_amp_case_a_direct import run_example as run_case_a
from toy_amp_case_b_cpa import run_example as run_case_b
from toy_amp_shared import shared_laser_spec_summary

DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-ab")

def run_comparison(*, out_dir: Path, seed: int, emit_plots: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    case_a = run_case_a(out_dir=out_dir / "case-a", seed=seed, emit_plots=emit_plots)
    case_b = run_case_b(out_dir=out_dir / "case-b", seed=seed, emit_plots=emit_plots)

    comparison = {
        "seed": seed,
        "laser_gen": {
            "source": "toy_amp_shared.build_shared_laser_gen",
            "shared_spec": shared_laser_spec_summary(),
        },
        "cases": {
            "A_direct": {
                "description": case_a["description"],
                "summary_path": str(out_dir / "case-a" / "run_summary.json"),
                "comparison_metrics": case_a["comparison_metrics"],
            },
            "B_cpa": {
                "description": case_b["description"],
                "summary_path": str(out_dir / "case-b" / "run_summary.json"),
                "comparison_metrics": case_b["comparison_metrics"],
            },
        },
    }

    (out_dir / "comparison_summary.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n"
    )
    return comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run toy amp cases A and B together and write side-by-side comparison output."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--emit-plots", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    comparison = run_comparison(out_dir=args.out, seed=args.seed, emit_plots=args.emit_plots)
    print(f"wrote comparison: {args.out / 'comparison_summary.json'}")
    print(f"compared metrics: {len(comparison['cases']['A_direct']['comparison_metrics'])}")


if __name__ == "__main__":
    main()
