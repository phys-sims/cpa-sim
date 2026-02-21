from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserSpec, LaserState, PulseGrid, PulseSpec, PulseState
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage

DEFAULT_OUT_DIR = Path("artifacts/fiber-example")


def _build_empty_state() -> LaserState:
    pulse = PulseState
    empty_pulse = pulse(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
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
                    shape="gaussian",
                    amplitude=5.0,
                    width_fs=80.0,
                    center_wavelength_nm=1030.0,
                    n_samples=512,
                    time_window_fs=2000.0,
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
                gamma_1_per_w_m=0.01,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.02]),
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

    plt: Any = import_module("matplotlib.pyplot")

    t_fs = np.asarray(initial.pulse.grid.t, dtype=float)
    w = np.asarray(initial.pulse.grid.w, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(t_fs, initial.pulse.intensity_t, label="input")
    ax.plot(t_fs, final.pulse.intensity_t, label="after fiber")
    ax.set_xlabel("Time (fs)")
    ax.set_ylabel("Intensity (arb. from |A|^2)")
    ax.set_title("WUST gnlse fiber example: time-domain intensity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["time"], format=plot_format)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(w, initial.pulse.spectrum_w, label="input")
    ax.plot(w, final.pulse.spectrum_w, label="after fiber")
    ax.set_xlabel("Angular frequency axis (rad/fs)")
    ax.set_ylabel("Spectrum (arb. from |Aw|^2)")
    ax.set_title("WUST gnlse fiber example: spectral magnitude")
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["spectrum"], format=plot_format)
    plt.close(fig)

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
