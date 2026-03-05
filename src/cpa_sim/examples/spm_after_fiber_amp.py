from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberAmpWrapCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PulseSpec,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.plotting import LineSeries, plot_line_series
from cpa_sim.stages.amp import FiberAmpWrapStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage

DEFAULT_OUT_DIR = Path("artifacts/spm-after-fiber-amp")


def _build_empty_state() -> LaserState:
    empty_pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1560.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(pulse=empty_pulse, beam=BeamState(radius_mm=1.0, m2=1.0))


def run_example(*, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    laser_stage = AnalyticLaserGenStage(
        LaserGenCfg(
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
        )
    )
    initial = laser_stage.process(_build_empty_state()).state

    amp_stage = FiberAmpWrapStage(
        FiberAmpWrapCfg(
            name="fiber_amp_spm",
            power_out_w=4.5,
            physics=FiberPhysicsCfg(
                length_m=2.0,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.025,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                z_saves=64,
                keep_full_solution=False,
            ),
        )
    )
    final_result = amp_stage.process(initial)
    final = final_result.state

    time_plot = out_dir / "spm_amp_time_intensity.svg"
    spectrum_plot = out_dir / "spm_amp_spectrum.svg"

    t_fs = np.asarray(initial.pulse.grid.t, dtype=float)
    w = np.asarray(initial.pulse.grid.w, dtype=float)

    plot_line_series(
        out_path=time_plot,
        series=[
            LineSeries(x=t_fs, y=np.asarray(initial.pulse.intensity_t, dtype=float), label="input"),
            LineSeries(
                x=t_fs,
                y=np.asarray(final.pulse.intensity_t, dtype=float),
                label="after fiber amp",
            ),
        ],
        x_label="Time (fs)",
        y_label="Intensity (arb. from |A|^2)",
        title="SPM after fiber amp stage: sech² 7 ps pulse",
        plot_format="svg",
    )

    plot_line_series(
        out_path=spectrum_plot,
        series=[
            LineSeries(x=w, y=np.asarray(initial.pulse.spectrum_w, dtype=float), label="input"),
            LineSeries(
                x=w, y=np.asarray(final.pulse.spectrum_w, dtype=float), label="after fiber amp"
            ),
        ],
        x_label="Angular frequency axis (rad/fs)",
        y_label="Spectrum (arb. from |Aw|^2)",
        title="SPM spectral broadening after fiber amp stage",
        plot_format="svg",
    )

    summary = {
        "inputs": {
            "shape": "sech2",
            "width_fs": 7000.0,
            "avg_power_in_w": 0.3,
            "avg_power_out_target_w": 4.5,
            "rep_rate_ghz": 1.115,
            "fiber_length_m": 2.0,
            "gamma_1_per_w_m": 0.025,
        },
        "metrics": final_result.metrics,
        "artifacts": {
            "time_intensity_svg": str(time_plot),
            "spectrum_svg": str(spectrum_plot),
        },
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
