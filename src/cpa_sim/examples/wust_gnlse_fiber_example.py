from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    RamanCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserSpec, LaserState, PulseGrid, PulseSpec, PulseState
from cpa_sim.plotting import LineSeries, plot_line_series
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage

DEFAULT_OUT_DIR = Path("artifacts/fiber-example")


def _build_empty_state() -> LaserState:
    pulse = PulseState
    empty_pulse = pulse(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1550.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(pulse=empty_pulse, beam=BeamState(radius_mm=1.0, m2=1.0))


def run_example(out_dir: Path, *, plot_format: str = "svg") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    laser_stage = AnalyticLaserGenStage(
        LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    avg_power_w=5,
                    width_fs=1000.0,
                    center_wavelength_nm=1550.0,
                    n_samples=1024,
                    time_window_fs=12000.0,
                )
            )
        )
    )
    initial = laser_stage.process(_build_empty_state()).state

    fiber_stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=0.25,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.008,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[-0.02]),
                raman=RamanCfg(model="blowwood"),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                z_saves=32,
                keep_full_solution=False,
            ),
        )
    )
    final = fiber_stage.process(initial).state
    paths = {
        "time": out_dir / f"fiber_time_intensity.{plot_format}",
        "spectrum": out_dir / f"fiber_spectrum.{plot_format}",
    }

    t_fs = np.asarray(initial.pulse.grid.t, dtype=float)
    w = np.asarray(initial.pulse.grid.w, dtype=float)

    plot_line_series(
        out_path=paths["time"],
        series=[
            LineSeries(x=t_fs, y=np.asarray(initial.pulse.intensity_t, dtype=float), label="input"),
            LineSeries(
                x=t_fs, y=np.asarray(final.pulse.intensity_t, dtype=float), label="after fiber"
            ),
        ],
        x_label="Time (fs)",
        y_label="Intensity (arb. from |A|^2)",
        title="WUST gnlse fiber example: 1550 nm / 1 ps pulse intensity",
        plot_format=plot_format,
    )

    plot_line_series(
        out_path=paths["spectrum"],
        series=[
            LineSeries(x=w, y=np.asarray(initial.pulse.spectrum_w, dtype=float), label="input"),
            LineSeries(x=w, y=np.asarray(final.pulse.spectrum_w, dtype=float), label="after fiber"),
        ],
        x_label="Angular frequency axis (rad/fs)",
        y_label="Spectrum (arb. from |Aw|^2)",
        title="WUST gnlse fiber example: nonlinear + Raman spectral evolution",
        plot_format=plot_format,
    )

    return paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a small WUST gnlse fiber example and save plots."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--format", choices=["svg", "pdf"], default="svg")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    outputs = run_example(args.out, plot_format=args.format)
    for name, path in outputs.items():
        print(f"wrote {name}: {path}")


if __name__ == "__main__":
    main()
