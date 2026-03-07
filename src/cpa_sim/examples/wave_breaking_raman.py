"""Reproduce dispersive-wave emission in anomalous-regime fiber propagation.

This script demonstrates supercontinuum dynamics where a femtosecond pulse launched in
anomalous dispersion emits a short-wavelength dispersive wave under higher-order
phase matching. The most important knobs are:

- higher-order dispersion (Taylor beta coefficients),
- Raman response model selection, and
- self-steepening (optical shock term).

Reference solver: the external WUST-FOG `gnlse` Python package. This setup is
aligned with WUST-FOG `gnlse` dispersive-wave / Raman examples
(`example_dispersive_wave`, `test_raman`) but executed through cpa-sim's
stage/config API so it can be used as a reproducible, user-facing workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from cpa_sim.examples._shared import print_example_artifacts, run_example_with_default_policy
from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RamanCfg,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz

_STAGE_NAME = "wave_breaking_raman"
DEFAULT_OUT_DIR = Path("artifacts/wave-breaking-raman")
DEFAULT_N_SAMPLES = 8192
DEFAULT_Z_SAVES = 400
RamanModelName = Literal["blowwood", "linagrawal", "hollenbeck", "none"]


def run_example(
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    n_samples: int = DEFAULT_N_SAMPLES,
    z_saves: int = DEFAULT_Z_SAVES,
    raman_model: RamanModelName = "blowwood",
) -> dict[str, Path]:
    """Run the WUST-FOG `gnlse`-aligned wave-breaking Raman example."""
    raman_cfg = None if raman_model == "none" else RamanCfg(model=raman_model)
    cfg = PipelineConfig(
        runtime=RuntimeCfg(seed=7),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    center_wavelength_nm=835.0,
                    shape="sech2",
                    width_fs=50.284,
                    peak_power_w=10000.0,
                    n_samples=n_samples,
                    time_window_fs=12500.0,
                )
            )
        ),
        stages=[
            FiberCfg(
                name=_STAGE_NAME,
                physics=FiberPhysicsCfg(
                    length_m=0.15,
                    loss_db_per_m=0.0,
                    gamma_1_per_w_m=0.11,
                    self_steepening=True,
                    dispersion=DispersionTaylorCfg(
                        betas_psn_per_m=[
                            -11.830e-3,
                            8.1038e-5,
                            -9.5205e-8,
                            2.0737e-10,
                            -5.3943e-13,
                            1.3486e-15,
                            -2.5495e-18,
                            3.0524e-21,
                            -1.7140e-24,
                        ]
                    ),
                    raman=raman_cfg,
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=z_saves,
                    keep_full_solution=True,
                ),
            )
        ],
    )

    run_output = run_example_with_default_policy(cfg, stage_plot_dir=out_dir)

    artifacts = run_output.artifacts
    z_traces_npz = Path(artifacts[f"{_STAGE_NAME}.z_traces_npz"])

    fig_paths = plot_dispersive_wave_maps_from_npz(
        npz_path=z_traces_npz,
        center_wavelength_nm=835.0,
        out_dir=out_dir,
        stem=_STAGE_NAME,
        compat_mode="wust",
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )

    return {
        "z_traces_npz": z_traces_npz,
        "wavelength_linear": fig_paths.wavelength_linear,
        "wavelength_log": fig_paths.wavelength_log,
        "delay_linear": fig_paths.delay_linear,
        "delay_log": fig_paths.delay_log,
    }


def main() -> None:
    outputs = run_example()
    print_example_artifacts(title="Generated wave-breaking Raman artifacts:", artifacts=outputs)


if __name__ == "__main__":
    main()
