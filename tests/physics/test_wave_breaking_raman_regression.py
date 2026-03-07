from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cpa_sim.examples.wave_breaking_raman import run_example

_LIGHT_SPEED_NM_PER_FS = 299.792458


def _wavelength_axis_nm(*, w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_fs = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / center_wavelength_nm
    omega_abs_rad_per_fs = omega0_rad_per_fs + np.asarray(w_rad_per_fs, dtype=float)
    wavelength_nm = np.full_like(omega_abs_rad_per_fs, np.nan, dtype=float)
    valid = omega_abs_rad_per_fs > 0.0
    wavelength_nm[valid] = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / omega_abs_rad_per_fs[valid]
    return wavelength_nm


def _load_npz_solution(npz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(npz_path) as payload:
        z_m = np.asarray(payload["z_m"], dtype=float)
        t_fs = np.asarray(payload["t_fs"], dtype=float)
        w_rad_per_fs = np.asarray(payload["w_rad_per_fs"], dtype=float)
        at_zt = np.asarray(payload["at_zt_real"], dtype=float) + 1j * np.asarray(
            payload["at_zt_imag"], dtype=float
        )
    return z_m, t_fs, w_rad_per_fs, at_zt


def _extract_observables(
    *, t_fs: np.ndarray, w_rad_per_fs: np.ndarray, at_zt: np.ndarray
) -> dict[str, float]:
    dt_fs = float(np.mean(np.diff(t_fs)))

    power_t_in = np.abs(np.asarray(at_zt[0], dtype=np.complex128)) ** 2
    power_t_out = np.abs(np.asarray(at_zt[-1], dtype=np.complex128)) ** 2
    energy_in = float(np.sum(power_t_in) * dt_fs)
    energy_out = float(np.sum(power_t_out) * dt_fs)

    aw_final = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt[-1])))
    power_w = np.abs(aw_final) ** 2
    wavelength_nm = _wavelength_axis_nm(w_rad_per_fs=w_rad_per_fs, center_wavelength_nm=835.0)

    finite = np.isfinite(wavelength_nm) & np.isfinite(power_w)
    if not np.any(finite):
        raise ValueError("Final wavelength/power arrays contain no finite samples.")

    blue = finite & (wavelength_nm >= 500.0) & (wavelength_nm <= 650.0)
    if not np.any(blue):
        raise ValueError("Blue-band mask [500, 650] nm is empty.")

    total_peak = float(np.nanmax(power_w[finite]))
    blue_peak = float(np.nanmax(power_w[blue]))
    blue_peak_wavelength_nm = float(wavelength_nm[blue][int(np.nanargmax(power_w[blue]))])
    global_peak_wavelength_nm = float(wavelength_nm[finite][int(np.nanargmax(power_w[finite]))])

    spectral_weight = np.clip(np.asarray(power_w[finite], dtype=float), 0.0, None)
    spectral_centroid_nm = float(
        np.sum(wavelength_nm[finite] * spectral_weight) / max(np.sum(spectral_weight), 1e-30)
    )

    delay_peak_ps = float(t_fs[int(np.argmax(power_t_out))] * 1e-3)
    t_ps = t_fs * 1e-3
    delay_weight = np.clip(np.asarray(power_t_out, dtype=float), 0.0, None)
    delay_mean_ps = float(np.sum(t_ps * delay_weight) / max(np.sum(delay_weight), 1e-30))
    delay_var_ps2 = float(
        np.sum(((t_ps - delay_mean_ps) ** 2) * delay_weight) / max(np.sum(delay_weight), 1e-30)
    )

    return {
        "energy_ratio": float(energy_out / max(energy_in, 1e-30)),
        "blue_peak_ratio": float(blue_peak / max(total_peak, 1e-30)),
        "blue_peak_wavelength_nm": blue_peak_wavelength_nm,
        "global_peak_wavelength_nm": global_peak_wavelength_nm,
        "spectral_centroid_nm": spectral_centroid_nm,
        "delay_peak_ps": delay_peak_ps,
        "delay_rms_ps": float(np.sqrt(max(delay_var_ps2, 0.0))),
    }


@pytest.mark.physics
@pytest.mark.gnlse
@pytest.mark.slow
def test_wave_breaking_raman_wust_regression_fixture_bounds(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "wave_breaking_raman_wust_regression.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cfg = fixture["config"]

    outputs = run_example(
        out_dir=tmp_path,
        n_samples=int(cfg["n_samples"]),
        z_saves=int(cfg["z_saves"]),
        raman_model=str(cfg["raman_model"]),
    )

    z_m, t_fs, w_rad_per_fs, at_zt = _load_npz_solution(outputs["z_traces_npz"])
    assert z_m.size == int(cfg["z_saves"])
    assert at_zt.shape == (int(cfg["z_saves"]), int(cfg["n_samples"]))

    observed = _extract_observables(t_fs=t_fs, w_rad_per_fs=w_rad_per_fs, at_zt=at_zt)
    for name, bounds in fixture["bounds"].items():
        value = observed[name]
        min_value = float(bounds["min"])
        max_value = float(bounds["max"])
        assert min_value <= value <= max_value, (
            f"{name} out of regression bounds: observed={value:.6g}, "
            f"expected_range=[{min_value:.6g}, {max_value:.6g}]"
        )
