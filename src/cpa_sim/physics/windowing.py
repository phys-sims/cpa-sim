from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from cpa_sim.models.state import LaserState, PulseGrid, PulseState
from cpa_sim.phys_pipeline_compat import PolicyBag
from cpa_sim.utils import _policy_get


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

    t_old = np.asarray(state.pulse.grid.t, dtype=np.float64)
    old_centroid_fs = intensity_weighted_mean_fs(t_old, np.abs(old_field_t) ** 2)

    field_t_new = np.zeros(new_n_samples, dtype=np.complex128)
    start = (new_n_samples - old_n) // 2
    stop = start + old_n
    field_t_new[start:stop] = old_field_t

    field_w_new = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t_new)))
    w_new = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(new_n_samples, d=dt))
    new_centroid_fs = intensity_weighted_mean_fs(t_new, np.abs(field_t_new) ** 2)
    centroid_shift_fs = old_centroid_fs - new_centroid_fs
    if centroid_shift_fs != 0.0:
        recenter_pulse_inplace(field_w_new, w_new, shift_fs=centroid_shift_fs)
        field_t_new = np.fft.fftshift(np.fft.ifft(np.fft.ifftshift(field_w_new)))

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


def _parse_stage_list(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


def auto_window_enabled_for_stage(policy: PolicyBag | None, *, stage_name: str) -> bool:
    enabled = bool(_policy_get(policy, "cpa.auto_window.enabled", False))
    if not enabled:
        return False
    stage_list = _parse_stage_list(_policy_get(policy, "cpa.auto_window.stages", None))
    if stage_list is None:
        return True
    return stage_name in stage_list


def _next_n_samples(n: int, *, growth_factor: float, prefer_pow2: bool) -> int:
    next_n = int(math.ceil(float(n) * float(growth_factor)))
    if prefer_pow2:
        next_n = 1 << max(0, next_n - 1).bit_length()
    return max(next_n, n + 1)


# NOTE: AutoWindow is currently intended ONLY for the existing free-space phase-only backends
# (Treacy grating pair and phase-only dispersion). Future dispersion-aware ray-tracing / spatial
# free-space backends may be expensive and should likely ignore/disable auto-window reruns
# by default.
def run_with_auto_window(
    state: LaserState,
    run_once: Callable[[LaserState], LaserState],
    *,
    stage_name: str,
    policy: PolicyBag | None,
) -> tuple[LaserState, dict[str, float], list[dict[str, object]]]:
    enabled = auto_window_enabled_for_stage(policy, stage_name=stage_name)
    metrics_prefix = f"{stage_name}.auto_window"

    if not enabled:
        out_state = run_once(state)
        metrics = {
            f"{metrics_prefix}_enabled": 0.0,
            f"{metrics_prefix}_attempts": 1.0,
            f"{metrics_prefix}_reruns": 0.0,
            f"{metrics_prefix}_n_in": float(len(state.pulse.field_t)),
            f"{metrics_prefix}_n_out": float(len(out_state.pulse.field_t)),
            f"{metrics_prefix}_edge_energy_fraction_final": 0.0,
            f"{metrics_prefix}_recenter_shift_fs_last": 0.0,
        }
        return out_state, metrics, []

    edge_fraction = float(_policy_get(policy, "cpa.auto_window.edge_fraction", 0.05))
    threshold = float(_policy_get(policy, "cpa.auto_window.max_edge_energy_fraction", 1e-6))
    max_iters = int(_policy_get(policy, "cpa.auto_window.max_iters", 6))
    growth_factor = float(_policy_get(policy, "cpa.auto_window.growth_factor", 2.0))
    prefer_pow2 = bool(_policy_get(policy, "cpa.auto_window.prefer_pow2", True))
    max_n_samples_raw = _policy_get(policy, "cpa.auto_window.max_n_samples", None)
    max_n_samples = None if max_n_samples_raw is None else int(max_n_samples_raw)
    recenter_each_iter = bool(_policy_get(policy, "cpa.auto_window.recenter_each_iter", True))
    verbose = bool(_policy_get(policy, "cpa.auto_window.print", False))
    nyquist_guard_fraction = float(
        _policy_get(policy, "cpa.auto_window.nyquist_guard_fraction", 0.05)
    )
    max_nyquist_energy_fraction = float(
        _policy_get(policy, "cpa.auto_window.max_nyquist_energy_fraction", 1e-6)
    )

    nyquist_energy_input = nyquist_energy_fraction(
        np.asarray(state.pulse.spectrum_w, dtype=np.float64),
        nyquist_guard_fraction=nyquist_guard_fraction,
    )
    if nyquist_energy_input > max_nyquist_energy_fraction:
        raise RuntimeError(
            "Auto-window input Nyquist guard energy is too large; this indicates a dt/Nyquist "
            "sampling issue that padding cannot fix. "
            f"stage={stage_name} nyquist_energy_fraction={nyquist_energy_input:.6e} "
            f"threshold={max_nyquist_energy_fraction:.6e}"
        )

    base_state = state
    n0 = int(len(base_state.pulse.field_t))
    n = n0
    events: list[dict[str, object]] = []

    attempts = 0
    n_final = float(n0)
    edge_final = 0.0
    shift_last = 0.0

    for attempt in range(max_iters + 1):
        attempts = attempt + 1
        trial_in = base_state if n == n0 else pad_laser_state_time(base_state, new_n_samples=n)
        trial_out = run_once(trial_in)
        if recenter_each_iter:
            trial_out, shift_fs = recenter_state_by_intensity_centroid(trial_out)
        else:
            shift_fs = 0.0

        n_current = int(len(trial_in.pulse.field_t))
        dt_fs = float(trial_in.pulse.grid.dt)
        time_window_fs = dt_fs * float(max(0, n_current - 1))
        edge = edge_energy_fraction(
            np.asarray(trial_out.pulse.intensity_t, dtype=np.float64), edge_fraction=edge_fraction
        )
        event: dict[str, object] = {
            "stage": stage_name,
            "attempt": attempt,
            "n_samples": n_current,
            "dt_fs": dt_fs,
            "time_window_fs": time_window_fs,
            "edge_fraction": edge_fraction,
            "edge_energy_fraction": float(edge),
            "threshold": threshold,
            "nyquist_guard_fraction": nyquist_guard_fraction,
            "nyquist_energy_fraction_input": float(nyquist_energy_input),
            "recenter_shift_fs": float(shift_fs),
        }
        events.append(event)

        n_final = float(n_current)
        edge_final = float(edge)
        shift_last = float(shift_fs)

        if edge <= threshold:
            metrics = {
                f"{metrics_prefix}_enabled": 1.0,
                f"{metrics_prefix}_attempts": float(attempts),
                f"{metrics_prefix}_reruns": float(max(0, attempts - 1)),
                f"{metrics_prefix}_n_in": float(n0),
                f"{metrics_prefix}_n_out": n_final,
                f"{metrics_prefix}_edge_energy_fraction_final": edge_final,
                f"{metrics_prefix}_recenter_shift_fs_last": shift_last,
            }
            return trial_out, metrics, events

        n_next = _next_n_samples(n_current, growth_factor=growth_factor, prefer_pow2=prefer_pow2)
        if max_n_samples is not None and n_next > max_n_samples:
            raise RuntimeError(
                "Auto-window exceeded max_n_samples before edge-energy threshold was met. "
                f"stage={stage_name} attempt={attempt} edge_energy_fraction={edge:.6e} "
                f"threshold={threshold:.6e} n_current={n_current} n_next={n_next} "
                f"max_n_samples={max_n_samples}"
            )

        if verbose:
            print(
                f"[auto-window] stage={stage_name} attempt={attempt} edge={edge:.6e} > "
                f"{threshold:.6e} -> pad N {n_current} -> {n_next} and rerun"
            )
        n = n_next

    raise RuntimeError(
        "Auto-window failed to reach edge-energy threshold within max_iters. "
        f"stage={stage_name} max_iters={max_iters} final_edge_energy_fraction={edge_final:.6e} "
        f"final_n_samples={int(n_final)}"
    )
