from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cpa_sim.models import (
    BeamSpec,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    ToyFiberAmpCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.pipeline import run_pipeline

DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-b")


def build_config(*, seed: int) -> PipelineConfig:
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=LaserGenCfg(
            name="laser_init_case_b",
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="gaussian",
                    amplitude=1.0,
                    width_fs=100.0,
                    center_wavelength_nm=1030.0,
                    n_samples=512,
                    time_window_fs=3000.0,
                ),
                beam=BeamSpec(radius_mm=1.0, m2=1.0),
            ),
        ),
        stages=[
            TreacyGratingPairCfg(
                name="stretcher",
                line_density_lpmm=1200.0,
                incidence_angle_deg=34.0,
                separation_um=80_000.0,
                wavelength_nm=1030.0,
                n_passes=2,
                include_tod=True,
                apply_to_pulse=True,
            ),
            ToyFiberAmpCfg(
                name="toy_amp",
                length_m=1.5,
                beta2_s2_per_m=0.0,
                gamma_w_inv_m=4e-3,
                gain_db=9.0,
                loss_db_per_m=0.0,
                n_steps=10,
            ),
            TreacyGratingPairCfg(
                name="compressor",
                line_density_lpmm=1200.0,
                incidence_angle_deg=34.0,
                separation_um=80_000.0,
                wavelength_nm=1030.0,
                n_passes=2,
                include_tod=True,
                apply_to_pulse=True,
            ),
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
        "description": "CPA-style stretcher -> toy amp -> compressor chain.",
        "metrics": result.metrics,
        "artifacts": {**result.artifacts, **result.state.artifacts},
    }
    (out_dir / "run_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run toy fiber amp case B (CPA chain).")
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
