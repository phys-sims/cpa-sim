from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

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
    # Stretch ~2 ps -> ~40 ps with positive GDD (fiber stretcher) before compression.
    target_stretch_ratio = 20.0
    input_width_ps = 2.0
    stretcher_length_m = 100.0
    stretcher_beta2_s2_per_m = (
        np.sqrt(target_stretch_ratio**2 - 1.0)
        * (input_width_ps * 1e-12) ** 2
        / (4.0 * np.log(2.0) * stretcher_length_m)
    )

    # EDFA-like toy gain block configured from an exponential gain coefficient (1 / m).
    edfa_length_m = 5.0
    edfa_gain_per_m = 1.0
    edfa_gain_db = float(10.0 * np.log10(np.exp(edfa_gain_per_m * edfa_length_m)))

    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=LaserGenCfg(
            name="laser_init_case_b",
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    amplitude=1.0,
                    width_fs=2_000.0,
                    center_wavelength_nm=1560.0,
                    n_samples=512,
                    time_window_fs=120_000.0,
                ),
                beam=BeamSpec(radius_mm=1.0, m2=1.0),
            ),
        ),
        stages=[
            ToyFiberAmpCfg(
                name="stretcher",
                length_m=stretcher_length_m,
                beta2_s2_per_m=float(stretcher_beta2_s2_per_m),
                gamma_w_inv_m=0.0,
                gain_db=0.0,
                loss_db_per_m=0.0,
                n_steps=20,
            ),
            ToyFiberAmpCfg(
                name="edfa",
                length_m=edfa_length_m,
                beta2_s2_per_m=0.0,
                gamma_w_inv_m=5e-3,
                gain_db=edfa_gain_db,
                loss_db_per_m=0.0,
                n_steps=20,
            ),
            TreacyGratingPairCfg(
                name="compressor",
                line_density_lpmm=600.0,
                incidence_angle_deg=20.0,
                separation_um=120_000.0,
                wavelength_nm=1560.0,
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
        "description": "CPA-style fiber stretcher -> EDFA-like toy fiber amp -> Treacy compressor chain.",
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
