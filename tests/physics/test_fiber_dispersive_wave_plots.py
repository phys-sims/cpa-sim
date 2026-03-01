from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    PipelineConfig,
    RamanCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.laser_gen import AnalyticLaserGenStage

_LIGHT_SPEED_NM_PER_FS = 299.792458
_BETAS_PSN_PER_M = [
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


def _seed_state(center_wavelength_nm: float) -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(
            t=[0.0, 1.0],
            w=[0.0, 1.0],
            dt=1.0,
            dw=1.0,
            center_wavelength_nm=center_wavelength_nm,
        ),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={},
        metrics={},
        artifacts={},
    )


def _wavelength_axis_nm(w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_fs = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / center_wavelength_nm
    omega_abs_rad_per_fs = omega0_rad_per_fs + w_rad_per_fs

    lam_nm = np.full_like(omega_abs_rad_per_fs, np.nan, dtype=float)
    valid = omega_abs_rad_per_fs > 0.0
    lam_nm[valid] = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / omega_abs_rad_per_fs[valid]
    return lam_nm


def _blue_band_peak_ratio(lam_nm: np.ndarray, power: np.ndarray) -> float:
    finite = np.isfinite(lam_nm) & np.isfinite(power)
    blue = finite & (lam_nm >= 500.0) & (lam_nm <= 650.0)
    if not np.any(blue):
        raise ValueError("Blue-band wavelength mask [500, 650] nm is empty or non-finite.")

    total_peak = float(np.nanmax(power[finite]))
    blue_peak = float(np.nanmax(power[blue]))
    return blue_peak / total_peak


def _load_full_solution(npz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(npz_path)
    z_m = np.asarray(data["z_m"], dtype=float)
    t_fs = np.asarray(data["t_fs"], dtype=float)
    w_rad_per_fs = np.asarray(data["w_rad_per_fs"], dtype=float)
    at_zt = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(data["at_zt_imag"], dtype=float)
    return z_m, t_fs, w_rad_per_fs, at_zt


def _plot_evolution(
    *,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    at_zt: np.ndarray,
    center_wavelength_nm: float,
    out_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    delay_power = np.abs(at_zt) ** 2
    aw_zw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)
    spectrum_power = np.abs(aw_zw) ** 2
    lam_nm = _wavelength_axis_nm(w_rad_per_fs, center_wavelength_nm)

    spec_log = np.log10(spectrum_power + 1e-30)
    delay_log = np.log10(delay_power + 1e-30)

    spec_vmax = float(np.nanmax(spec_log))
    spec_vmin = spec_vmax - 50.0
    delay_vmax = float(np.nanmax(delay_log))
    delay_vmin = delay_vmax - 50.0

    fig, (ax_spec, ax_delay) = plt.subplots(ncols=2, figsize=(12, 4.8), constrained_layout=True)

    m_spec = ax_spec.pcolormesh(
        z_m,
        lam_nm,
        np.clip(spec_log.T, spec_vmin, spec_vmax),
        shading="auto",
        cmap="viridis",
    )
    fig.colorbar(m_spec, ax=ax_spec, label=r"$\log_{10}(|A(\omega, z)|^2)$")
    ax_spec.set_xlabel("Distance (m)")
    ax_spec.set_ylabel("Wavelength (nm)")
    ax_spec.set_title("Wavelength vs distance")

    m_delay = ax_delay.pcolormesh(
        z_m,
        t_fs / 1000.0,
        np.clip(delay_log.T, delay_vmin, delay_vmax),
        shading="auto",
        cmap="magma",
    )
    fig.colorbar(m_delay, ax=ax_delay, label=r"$\log_{10}(|A(t, z)|^2)$")
    ax_delay.set_xlabel("Distance (m)")
    ax_delay.set_ylabel("Delay (ps)")
    ax_delay.set_title("Delay vs distance")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


@pytest.mark.physics
@pytest.mark.gnlse
@pytest.mark.slow
@pytest.mark.parametrize(
    ("raman_cfg", "suffix", "expect_blue_ratio"),
    [
        pytest.param(RamanCfg(model="blowwood"), "blowwood", True, id="blowwood"),
        pytest.param(RamanCfg(model="hollenbeck"), "hollenbeck", True, id="hollenbeck"),
        pytest.param(None, "no_raman", False, id="no-raman"),
    ],
)
def test_fiber_dispersive_wave_evolution_plots(
    raman_cfg: RamanCfg | None,
    suffix: str,
    expect_blue_ratio: bool,
    tmp_path: Path,
) -> None:
    pytest.importorskip("gnlse")

    n_samples = 2**13
    z_saves = 300

    initial = (
        AnalyticLaserGenStage(
            PipelineConfig(
                laser_gen={
                    "spec": {
                        "pulse": {
                            "center_wavelength_nm": 835.0,
                            "shape": "sech2",
                            "width_fs": 50.284,
                            "peak_power_w": 10000.0,
                            "n_samples": n_samples,
                            "time_window_fs": 12500.0,
                        }
                    }
                }
            ).laser_gen
        )
        .process(_seed_state(center_wavelength_nm=835.0))
        .state
    )

    result = FiberStage(
        FiberCfg(
            name=f"fiber_{suffix}",
            physics=FiberPhysicsCfg(
                length_m=0.15,
                gamma_1_per_w_m=0.11,
                self_steepening=True,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=_BETAS_PSN_PER_M),
                raman=raman_cfg,
            ),
            numerics=WustGnlseNumericsCfg(
                z_saves=z_saves,
                method="RK45",
                rtol=1e-5,
                atol=1e-8,
                time_window_override_ps=12.5,
                keep_full_solution=True,
            ),
        )
    ).process(initial, policy={"cpa.stage_plot_dir": str(tmp_path / "stage_plots")})

    npz_path = Path(result.state.artifacts[f"fiber_{suffix}.z_traces_npz"])
    assert npz_path.exists(), f"Expected full-solution trace file at {npz_path}."

    z_m, t_fs, w_rad_per_fs, at_zt = _load_full_solution(npz_path)
    assert at_zt.shape == (z_saves, n_samples)
    assert z_m.shape == (z_saves,)
    assert t_fs.shape == (n_samples,)
    assert w_rad_per_fs.shape == (n_samples,)

    final_aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt[-1])))
    final_power = np.abs(final_aw) ** 2
    lam_nm = _wavelength_axis_nm(w_rad_per_fs, center_wavelength_nm=835.0)

    assert np.nanmax(final_power) > 0.0
    if expect_blue_ratio:
        blue_ratio = _blue_band_peak_ratio(lam_nm, final_power)
        assert blue_ratio >= 1e-4, (
            f"Expected robust blue-band feature for {suffix}, got blue_ratio={blue_ratio:.6g}."
        )

    artifact_dir = os.environ.get("CPA_SIM_ARTIFACT_DIR")
    if not artifact_dir:
        return

    out_path = Path(artifact_dir) / f"dispersive_wave_evolution_{suffix}.png"
    try:
        _plot_evolution(
            z_m=z_m,
            t_fs=t_fs,
            w_rad_per_fs=w_rad_per_fs,
            at_zt=at_zt,
            center_wavelength_nm=835.0,
            out_path=out_path,
        )
    except Exception:
        # Plot generation is optional and must not hide simulation regressions.
        return

    assert out_path.exists(), f"Expected evolution plot at {out_path}."
