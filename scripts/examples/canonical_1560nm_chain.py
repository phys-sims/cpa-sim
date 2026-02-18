from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cpa_sim.models import (
    AmpCfg,
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.pipeline import run_pipeline

DEFAULT_OUT_DIR = Path("artifacts/canonical-1560nm-chain")
DEFAULT_PLOT_DIR = DEFAULT_OUT_DIR / "stage-plots"
DEFAULT_SEED = 1560


def build_config(*, seed: int, ci_safe: bool) -> PipelineConfig:
    if ci_safe:
        n_samples = 256
        time_window_fs = 2400.0
        fiber_length_m = 0.25
    else:
        n_samples = 1024
        time_window_fs = 6000.0
        fiber_length_m = 1.0

    laser_gen = LaserGenCfg(
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="gaussian",
                amplitude=1.0,
                width_fs=120.0,
                center_wavelength_nm=1560.0,
                n_samples=n_samples,
                time_window_fs=time_window_fs,
            )
        )
    )

    stages = [
        FiberCfg(
            name="fiber_dcf_1560nm",
            physics=FiberPhysicsCfg(
                length_m=fiber_length_m,
                loss_db_per_m=0.2,
                gamma_1_per_w_m=0.003,
                dispersion=DispersionTaylorCfg(
                    # ADR sign convention: anomalous beta2 is negative.
                    betas_psn_per_m=[-0.022],
                ),
            ),
        ),
        AmpCfg(
            name="edfa_like_gain",
            kind="simple_gain",
            gain_linear=4.0,
        ),
        TreacyGratingPairCfg(
            name="treacy_compressor",
            line_density_lpmm=600.0,
            incidence_angle_deg=20.0,
            separation_um=120_000.0,
            wavelength_nm=1560.0,
            n_passes=2,
            include_tod=True,
            apply_to_pulse=True,
        ),
    ]

    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=laser_gen,
        stages=stages,
    )


def run_example(
    *,
    out_dir: Path,
    plot_dir: Path,
    seed: int,
    ci_safe: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = build_config(seed=seed, ci_safe=ci_safe)
    policy = {
        "cpa.emit_stage_plots": True,
        "cpa.stage_plot_dir": str(plot_dir),
    }
    result = run_pipeline(cfg, policy=policy)

    payload = {
        "seed": seed,
        "ci_safe": ci_safe,
        "policy": policy,
        "metrics": result.metrics,
        "artifacts": {**result.artifacts, **result.state.artifacts},
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a canonical 1560 nm CPA chain with DCF prechirp and Treacy compression."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for run_summary.json and other emitted files.",
    )
    parser.add_argument(
        "--plot-dir",
        type=Path,
        default=DEFAULT_PLOT_DIR,
        help="Directory for per-stage time/spectrum plots.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Deterministic runtime seed.",
    )
    parser.add_argument(
        "--ci-safe",
        action="store_true",
        help="Use a tiny-grid, short-fiber configuration for CI-safe runtime.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    output = run_example(
        out_dir=args.out,
        plot_dir=args.plot_dir,
        seed=args.seed,
        ci_safe=args.ci_safe,
    )
    print(f"wrote summary: {args.out / 'run_summary.json'}")
    print(f"artifacts emitted: {len(output['artifacts'])}")


if __name__ == "__main__":
    main()
