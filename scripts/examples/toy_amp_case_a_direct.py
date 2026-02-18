from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cpa_sim.models import PipelineConfig, RuntimeCfg, ToyFiberAmpCfg
from cpa_sim.pipeline import run_pipeline
from toy_amp_shared import build_shared_laser_gen

def _metric_by_suffix(metrics: dict[str, Any], suffix: str) -> float | None:
    for key, value in metrics.items():
        if key.endswith(suffix):
            return value
    return None


DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-a")


def build_config(*, seed: int) -> PipelineConfig:
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=build_shared_laser_gen(),
        stages=[
            ToyFiberAmpCfg(
                name="toy_amp",
                length_m=1.5,
                beta2_s2_per_m=0.0,
                gamma_w_inv_m=4e-3,
                gain_db=9.0,
                loss_db_per_m=0.0,
                n_steps=10,
            )
        ],
    )


def run_example(*, out_dir: Path, seed: int, emit_plots: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    policy = {
        "cpa.emit_stage_plots": emit_plots,
        "cpa.stage_plot_dir": str(out_dir / "stage-plots"),
    }
    result = run_pipeline(build_config(seed=seed), policy=policy)
    payload = {
        "seed": seed,
        "matching_criterion": "output_energy",
        "description": "Direct seed pulse into toy fiber amp with SPM enabled.",
        "comparison_metrics": {
            "energy_in_au": _metric_by_suffix(result.metrics, ".energy_in_au"),
            "energy_out_au": _metric_by_suffix(result.metrics, ".energy_out_au"),
            "peak_power_in_au": _metric_by_suffix(result.metrics, ".peak_power_in_au"),
            "peak_power_out_au": _metric_by_suffix(result.metrics, ".peak_power_out_au"),
            "bandwidth_in_rad_per_fs": _metric_by_suffix(result.metrics, ".bandwidth_in_rad_per_fs"),
            "bandwidth_out_rad_per_fs": _metric_by_suffix(result.metrics, ".bandwidth_out_rad_per_fs"),
            "b_integral_proxy_rad": _metric_by_suffix(result.metrics, ".b_integral_proxy_rad"),
            "pipeline.final_energy_au": _metric_by_suffix(result.metrics, ".summary.energy_au"),
            "pipeline.final_peak_power_au": _metric_by_suffix(result.metrics, ".summary.peak_intensity_au"),
            "pipeline.final_bandwidth_rad_per_fs": _metric_by_suffix(result.metrics, ".summary.bandwidth_rad_per_fs"),
        },
        "metrics": result.metrics,
        "artifacts": {**result.artifacts, **result.state.artifacts},
    }
    (out_dir / "run_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run toy fiber amp case A (direct amplification).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--emit-plots", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = run_example(out_dir=args.out, seed=args.seed, emit_plots=args.emit_plots)
    print(f"wrote summary: {args.out / 'run_summary.json'}")
    print(f"metrics emitted: {len(payload['metrics'])}")


if __name__ == "__main__":
    main()
