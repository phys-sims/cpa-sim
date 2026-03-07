from __future__ import annotations

from pathlib import Path
from typing import Any

from cpa_sim.examples._shared import (
    print_example_artifacts,
    run_example_with_default_policy,
    write_example_json,
)
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

DEFAULT_OUT_DIR = Path("artifacts/fiber-amp-spm")
DEFAULT_STAGE_NAME = "fiber_amp_spm"


def run_example(*, out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
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
    run_output = run_example_with_default_policy(cfg, stage_plot_dir=out_dir)
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
            "metrics_time_overlay_svg": run_output.artifacts["metrics.plot_time_intensity_overlay"],
            "metrics_spectrum_overlay_svg": run_output.artifacts["metrics.plot_spectrum_overlay"],
        },
    }

    write_example_json(out_dir / "summary.json", summary)
    return summary


def main() -> None:
    summary = run_example()
    print_example_artifacts(
        title="Generated fiber amp SPM artifacts:",
        artifacts={k: Path(v) for k, v in summary["artifacts"].items()},
    )
    print(f"  summary_json: {DEFAULT_OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
