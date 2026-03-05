from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.physics import (
    intensity_weighted_mean_fs,
    pad_laser_state_time,
    recenter_state_by_intensity_centroid,
)


def _make_gaussian_state(*, n_samples: int, dt_fs: float, center_fs: float) -> LaserState:
    time_window_fs = dt_fs * (n_samples - 1)
    t = np.linspace(-0.5 * time_window_fs, 0.5 * time_window_fs, n_samples)
    intensity = np.exp(-(((t - center_fs) / 35.0) ** 2))
    field_t = np.sqrt(intensity).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(n_samples, d=dt_fs))

    pulse = PulseState(
        grid=PulseGrid(
            t=t.tolist(),
            w=w.tolist(),
            dt=dt_fs,
            dw=float(w[1] - w[0]),
            center_wavelength_nm=1030.0,
        ),
        field_t=field_t,
        field_w=field_w,
        intensity_t=np.abs(field_t) ** 2,
        spectrum_w=np.abs(field_w) ** 2,
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={"hello": "world"},
        metrics={"x": 1.0},
        artifacts={"a": "b"},
    )


@pytest.mark.unit
def test_pad_laser_state_time_preserves_energy_and_dt() -> None:
    state = _make_gaussian_state(n_samples=256, dt_fs=2.0, center_fs=25.0)

    padded = pad_laser_state_time(state, new_n_samples=512)

    energy_before = float(np.sum(state.pulse.intensity_t) * state.pulse.grid.dt)
    energy_after = float(np.sum(padded.pulse.intensity_t) * padded.pulse.grid.dt)

    assert padded.pulse.grid.dt == pytest.approx(state.pulse.grid.dt)
    assert energy_after == pytest.approx(energy_before, rel=0.0, abs=1e-10)


@pytest.mark.unit
def test_pad_laser_state_time_updates_window_from_dt_and_n() -> None:
    state = _make_gaussian_state(n_samples=128, dt_fs=1.25, center_fs=0.0)

    padded = pad_laser_state_time(state, new_n_samples=256)

    t_new = np.asarray(padded.pulse.grid.t)
    expected_window_fs = padded.pulse.grid.dt * (len(t_new) - 1)
    measured_window_fs = float(t_new[-1] - t_new[0])

    assert measured_window_fs == pytest.approx(expected_window_fs)


@pytest.mark.unit
def test_pad_laser_state_time_preserves_centroid_across_parity_change() -> None:
    state = _make_gaussian_state(n_samples=256, dt_fs=2.0, center_fs=25.0)
    initial_t = np.asarray(state.pulse.grid.t)
    initial_centroid_fs = intensity_weighted_mean_fs(initial_t, np.asarray(state.pulse.intensity_t))

    padded = pad_laser_state_time(state, new_n_samples=257)

    padded_t = np.asarray(padded.pulse.grid.t)
    padded_centroid_fs = intensity_weighted_mean_fs(padded_t, np.asarray(padded.pulse.intensity_t))

    assert padded_centroid_fs == pytest.approx(initial_centroid_fs, abs=1e-6)


@pytest.mark.unit
def test_recenter_state_by_intensity_centroid_moves_centroid_to_zero() -> None:
    state = _make_gaussian_state(n_samples=512, dt_fs=1.0, center_fs=42.5)
    t = np.asarray(state.pulse.grid.t)
    initial_centroid_fs = intensity_weighted_mean_fs(t, np.asarray(state.pulse.intensity_t))

    recentered, shift_fs = recenter_state_by_intensity_centroid(state)

    new_t = np.asarray(recentered.pulse.grid.t)
    new_centroid_fs = intensity_weighted_mean_fs(new_t, np.asarray(recentered.pulse.intensity_t))

    assert shift_fs == pytest.approx(initial_centroid_fs, abs=1e-9)
    assert new_centroid_fs == pytest.approx(0.0, abs=1e-6)
