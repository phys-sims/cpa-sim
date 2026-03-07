"""Reproduce dispersive-wave emission in anomalous-regime fiber propagation.

This script demonstrates supercontinuum dynamics where a femtosecond pulse launched in
anomalous dispersion emits a short-wavelength dispersive wave under higher-order
phase matching. The most important knobs are:

- higher-order dispersion (Taylor beta coefficients),
- Raman response model selection, and
- self-steepening (optical shock term).

The setup is aligned with the `gnlse-python` dispersive-wave / Raman examples
(`example_dispersive_wave`, `test_raman`) but executed through cpa-sim's stage/config
API so it can be used as a reproducible, user-facing workflow.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

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
from cpa_sim.pipeline import run_pipeline
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz

_STAGE_NAME = "wave_breaking_raman"
RamanModelName = Literal["blowwood", "linagrawal", "hollenbeck", "none"]


def _int_with_min(*, name: str, minimum: int) -> Callable[[str], int]:
    def _parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be an integer.") from exc
        if parsed < minimum:
            raise argparse.ArgumentTypeError(f"{name} must be >= {minimum}; got {parsed}.")
        return parsed

    return _parse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate dispersive-wave figures with cpa-sim + WUST gnlse"
    )
    parser.add_argument(
        "--outdir", type=Path, required=True, help="Output directory for generated figures"
    )
    parser.add_argument(
        "--n-samples",
        type=_int_with_min(name="--n-samples", minimum=2),
        default=8192,
        help="Pulse temporal grid sample count (must be >= 2)",
    )
    parser.add_argument(
        "--z-saves",
        type=_int_with_min(name="--z-saves", minimum=1),
        default=400,
        help="Number of saved z-slices from gnlse (must be >= 1)",
    )
    parser.add_argument(
        "--raman-model",
        type=str,
        default="blowwood",
        choices=["blowwood", "linagrawal", "hollenbeck", "none"],
        help="Raman response model (or 'none' to disable Raman)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Quick mode: overrides to n_samples=4096 and z_saves=150",
    )
    return parser


def run_example(
    *,
    out_dir: Path,
    n_samples: int = 8192,
    z_saves: int = 400,
    raman_model: RamanModelName = "blowwood",
) -> dict[str, Path]:
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

    result = run_pipeline(
        cfg,
        policy={
            "cpa.emit_stage_plots": True,
            "cpa.stage_plot_dir": str(out_dir),
        },
    )

    artifacts = {**result.artifacts, **result.state.artifacts}
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
    args = _build_parser().parse_args()
    outdir = args.outdir

    n_samples = 4096 if args.fast else args.n_samples
    z_saves = 150 if args.fast else args.z_saves

    outputs = run_example(
        out_dir=outdir,
        n_samples=n_samples,
        z_saves=z_saves,
        raman_model=cast(RamanModelName, args.raman_model),
    )

    print("Generated wave-breaking Raman artifacts:")
    print(f"  z-traces npz       : {outputs['z_traces_npz']}")
    print(f"  wavelength (linear): {outputs['wavelength_linear']}")
    print(f"  wavelength (log)   : {outputs['wavelength_log']}")
    print(f"  delay (linear)     : {outputs['delay_linear']}")
    print(f"  delay (log)        : {outputs['delay_log']}")


if __name__ == "__main__":
    main()
