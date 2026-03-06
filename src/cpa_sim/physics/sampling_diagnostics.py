from __future__ import annotations

from cpa_sim.models.state import LaserState
from cpa_sim.physics.windowing import edge_energy_fraction, nyquist_energy_fraction


def time_edge_fraction(state: LaserState, *, edge_fraction: float) -> float:
    """Return the fractional temporal energy that sits near window edges."""
    return edge_energy_fraction(state.pulse.intensity_t, edge_fraction=edge_fraction)


def nyquist_guard_fraction(state: LaserState, *, guard_fraction: float) -> float:
    """Return the fractional spectral energy in Nyquist guard regions."""
    return nyquist_energy_fraction(state.pulse.spectrum_w, nyquist_guard_fraction=guard_fraction)


def grid_summary(state: LaserState) -> dict[str, float | int]:
    """Return compact sampling-grid summary diagnostics."""
    n_samples = int(len(state.pulse.grid.t))
    dt_fs = float(state.pulse.grid.dt)
    return {
        "n_samples": n_samples,
        "dt_fs": dt_fs,
        "time_window_fs": dt_fs * float(max(n_samples - 1, 0)),
        "dw": float(state.pulse.grid.dw),
    }
