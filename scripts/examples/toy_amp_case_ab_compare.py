from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from toy_amp_case_a_direct import run_example as run_case_a
from toy_amp_case_b_cpa import run_example as run_case_b

DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-ab")

METRICS_TO_COMPARE = (
    "laser.energy_au",
    "toy_amp.energy_in_au",
    "toy_amp.energy_out_au",
    "toy_amp.peak_power_in_au",
    "toy_amp.peak_power_out_au",
    "toy_amp.bandwidth_in_rad_per_fs",
    "toy_amp.bandwidth_out_rad_per_fs",
    "toy_amp.b_integral_proxy_rad",
    "pipeline.final_energy_au",
    "pipeline.final_peak_power_au",
    "pipeline.final_bandwidth_rad_per_fs",
)


def _extract_metrics(payload: dict[str, Any]) -> dict[str, float | None]:
    raw = payload.get("metrics", {})
    return {name: raw.get(name) for name in METRICS_TO_COMPARE}


def run_comparison(*, out_dir: Path, seed: int, emit_plots: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    case_a = run_case_a(out_dir=out_dir / "case-a", seed=seed, emit_plots=emit_plots)
    case_b = run_case_b(out_dir=out_dir / "case-b", seed=seed, emit_plots=emit_plots)

    comparison = {
        "seed": seed,
        "laser_gen_is_explicit": {
            "case_a": "laser_init_case_a",
            "case_b": "laser_init_case_b",
            "shared_spec": {
                "shape": "gaussian",
                "amplitude": 1.0,
                "width_fs": 100.0,
                "center_wavelength_nm": 1030.0,
                "n_samples": 512,
                "time_window_fs": 3000.0,
            },
        },
        "cases": {
            "A_direct": {
                "description": case_a["description"],
                "summary_path": str(out_dir / "case-a" / "run_summary.json"),
                "metrics": _extract_metrics(case_a),
            },
            "B_cpa": {
                "description": case_b["description"],
                "summary_path": str(out_dir / "case-b" / "run_summary.json"),
                "metrics": _extract_metrics(case_b),
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
    print(f"compared metrics: {len(comparison['cases']['A_direct']['metrics'])}")


if __name__ == "__main__":
    main()
