from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberAmpWrapCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.reporting import run_pipeline_with_plot_policy, write_json

DEFAULT_OUT_DIR = Path("artifacts/spm-after-fiber-amp")
DEFAULT_STAGE_NAME = "fiber_amp_spm"


def run_example(*, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=7),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    width_fs=7000.0,
                    avg_power_w=0.3,
                    rep_rate_mhz=1115.0,
                    center_wavelength_nm=1560.0,
                    n_samples=2048,
                    time_window_fs=100000.0,
                )
            )
        ),
        stages=[
            FiberAmpWrapCfg(
                name=DEFAULT_STAGE_NAME,
                power_out_w=4.5,
                physics=FiberPhysicsCfg(
                    length_m=14.0,
                    loss_db_per_m=0.0,
                    n2_m2_per_w=2.6e-20,
                    aeff_m2=4.18879020478639e-12,
                    dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=64,
                    keep_full_solution=False,
                ),
            )
        ],
    )
    run_output = run_pipeline_with_plot_policy(cfg, stage_plot_dir=out_dir)
    summary = {
        "inputs": {
            "shape": "sech2",
            "width_fs": 7000.0,
            "avg_power_in_w": 0.3,
            "avg_power_out_target_w": 4.5,
            "rep_rate_ghz": 1.115,
            "fiber_length_m": 14.0,
            "n2_m2_per_w": 2.6e-20,
            "aeff_m2": 4.18879020478639e-12,
        },
        "metrics": run_output.result.metrics,
        "artifacts": {
            "time_intensity_svg": run_output.artifacts[f"{DEFAULT_STAGE_NAME}.plot_time_intensity"],
            "spectrum_svg": run_output.artifacts[f"{DEFAULT_STAGE_NAME}.plot_spectrum"],
        },
    }

    write_json(out_dir / "summary.json", summary)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show SPM after a fiber amp stage at 0.3 W in / 4.5 W out average power."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_example(out_dir=args.out)
    print(f"wrote summary: {args.out / 'summary.json'}")


if __name__ == "__main__":
    main()
