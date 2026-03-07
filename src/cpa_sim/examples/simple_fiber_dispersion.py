from __future__ import annotations

from pathlib import Path

from cpa_sim.examples._shared import print_example_artifacts, run_example_with_default_policy
from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)

DEFAULT_OUT_DIR = Path("artifacts/simple-fiber-dispersion")
DEFAULT_STAGE_NAME = "simple_fiber_dispersion"


def run_example(out_dir: Path = DEFAULT_OUT_DIR, *, plot_format: str = "svg") -> dict[str, Path]:
    if plot_format != "svg":
        msg = "Only svg output is supported by stage plot policy."
        raise ValueError(msg)

    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=7),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    peak_power_w=5,
                    width_fs=1000.0,
                    center_wavelength_nm=1550.0,
                    n_samples=1024,
                    time_window_fs=12000.0,
                )
            )
        ),
        stages=[
            FiberCfg(
                name=DEFAULT_STAGE_NAME,
                physics=FiberPhysicsCfg(
                    length_m=0.3,
                    loss_db_per_m=0.0,
                    gamma_1_per_w_m=0.0,
                    dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.03]),
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=32,
                    keep_full_solution=False,
                ),
            )
        ],
    )

    run_output = run_example_with_default_policy(cfg, stage_plot_dir=out_dir)
    artifacts = run_output.artifacts
    return {
        "time_before_svg": Path(artifacts["laser_init.plot_time_intensity"]),
        "spectrum_before_svg": Path(artifacts["laser_init.plot_spectrum"]),
        "time_after_svg": Path(artifacts[f"{DEFAULT_STAGE_NAME}.plot_time_intensity"]),
        "spectrum_after_svg": Path(artifacts[f"{DEFAULT_STAGE_NAME}.plot_spectrum"]),
        "metrics_time_overlay_svg": Path(artifacts["metrics.plot_time_intensity_overlay"]),
        "metrics_spectrum_overlay_svg": Path(artifacts["metrics.plot_spectrum_overlay"]),
    }


def main() -> None:
    outputs = run_example()
    print_example_artifacts(title="Generated simple fiber dispersion artifacts:", artifacts=outputs)


if __name__ == "__main__":
    main()
