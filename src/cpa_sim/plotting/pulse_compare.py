from __future__ import annotations

from pathlib import Path

import numpy as np

from cpa_sim.models.state import LaserState

from .common import LineSeries, plot_line_series


def plot_pulse_comparison(
    *,
    initial: LaserState,
    final: LaserState,
    out_dir: Path,
    stem: str,
    plot_format: str = "svg",
) -> dict[str, Path]:
    """Save time/spectrum comparison plots for an initial/final pulse pair."""
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "time": out_dir / f"{stem}_time_intensity.{plot_format}",
        "spectrum": out_dir / f"{stem}_spectrum.{plot_format}",
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
