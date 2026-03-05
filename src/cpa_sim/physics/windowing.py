from __future__ import annotations

import math

import numpy as np

from cpa_sim.models.state import LaserState, PulseGrid, PulseState


def intensity_weighted_mean_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    """Return intensity-weighted mean time in femtoseconds."""
    total = float(np.sum(intensity))
    if total <= 0.0:
        return 0.0
    return float(np.sum(t_fs * intensity) / total)


def intensity_rms_width_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    """Return intensity-weighted RMS width in femtoseconds."""
    total = float(np.sum(intensity))
    if total <= 0.0:
        return 0.0
    mean_t = intensity_weighted_mean_fs(t_fs, intensity)
    variance = float(np.sum(((t_fs - mean_t) ** 2) * intensity) / total)
    return float(np.sqrt(max(variance, 0.0)))


def edge_energy_fraction(values: np.ndarray, *, edge_fraction: float) -> float:
    """Return fractional energy in edge guard bins for a nonnegative quantity."""
    n = int(values.size)
    if n == 0:
        return 0.0
    if not 0.0 <= edge_fraction <= 1.0:
        raise ValueError("edge_fraction must be between 0 and 1.")

    k = int(math.ceil(edge_fraction * n))
    if k <= 0:
        return 0.0

    total = float(np.sum(values))
    if total <= 0.0:
        return 0.0

    k = min(k, n)
    if 2 * k >= n:
        edge_sum = float(np.sum(values))
    else:
        edge_sum = float(np.sum(values[:k]) + np.sum(values[-k:]))
    return edge_sum / total


def nyquist_energy_fraction(spectrum: np.ndarray, *, nyquist_guard_fraction: float) -> float:
    """Return fractional spectral energy near Nyquist edges."""
    return edge_energy_fraction(spectrum, edge_fraction=nyquist_guard_fraction)


def recenter_pulse_inplace(field_w: np.ndarray, w: np.ndarray, *, shift_fs: float) -> np.ndarray:
    """Apply time-origin gauge shift in spectral domain and return updated field."""
    field_w *= np.exp(-1j * w * shift_fs)
    return field_w


def recenter_state_by_intensity_centroid(state: LaserState) -> tuple[LaserState, float]:
    """Return copied state recentered so intensity centroid in time is near zero."""
    out = state.deepcopy()

    t = np.asarray(out.pulse.grid.t, dtype=np.float64)
    w = np.asarray(out.pulse.grid.w, dtype=np.float64)
    shift_fs = intensity_weighted_mean_fs(t, np.asarray(out.pulse.intensity_t, dtype=np.float64))

    field_w = np.array(out.pulse.field_w, dtype=np.complex128, copy=True)
    recenter_pulse_inplace(field_w, w, shift_fs=-shift_fs)
    field_t = np.fft.fftshift(np.fft.ifft(np.fft.ifftshift(field_w)))
    intensity_t = np.abs(field_t) ** 2
    spectrum_w = np.abs(field_w) ** 2

    out.pulse = PulseState(
        grid=out.pulse.grid,
        field_t=field_t,
        field_w=field_w,
        intensity_t=intensity_t,
        spectrum_w=spectrum_w,
    )
    return out, shift_fs


def pad_laser_state_time(state: LaserState, *, new_n_samples: int) -> LaserState:
    """Return copied state with zero-padded time-domain field and updated frequency grid."""
    old_field_t = np.asarray(state.pulse.field_t)
    old_n = int(old_field_t.size)
    if new_n_samples < old_n:
        raise ValueError("new_n_samples must be >= current number of samples.")
    if new_n_samples < 2:
        raise ValueError("new_n_samples must be >= 2.")

    dt = float(state.pulse.grid.dt)
    t_new_window = dt * (new_n_samples - 1)
    t_new = np.linspace(-0.5 * t_new_window, 0.5 * t_new_window, new_n_samples)

    field_t_new = np.zeros(new_n_samples, dtype=np.complex128)
    start = (new_n_samples - old_n) // 2
    stop = start + old_n
    field_t_new[start:stop] = old_field_t

    field_w_new = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t_new)))
    w_new = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(new_n_samples, d=dt))
    dw_new = float(w_new[1] - w_new[0])

    out = state.deepcopy()
    out.pulse = PulseState(
        grid=PulseGrid(
            t=t_new.tolist(),
            w=w_new.tolist(),
            dt=dt,
            dw=dw_new,
            center_wavelength_nm=state.pulse.grid.center_wavelength_nm,
        ),
        field_t=field_t_new,
        field_w=field_w_new,
        intensity_t=np.abs(field_t_new) ** 2,
        spectrum_w=np.abs(field_w_new) ** 2,
    )
    return out
