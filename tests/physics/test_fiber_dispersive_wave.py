# Derived from the gnlse-python dispersive-wave (test_raman) example to validate
# dispersion-driven spectral-wave generation (high-order dispersion + Raman + shock),
# not just pure SPM broadening.
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

_LIGHT_SPEED_NM_PER_FS = 299.792458  # c in nm/fs for wavelength conversion on fs grids.


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


def compute_energy(pulse: PulseState) -> float:
    power_t_w = np.abs(np.asarray(pulse.field_t, dtype=np.complex128)) ** 2
    dt_fs = float(pulse.grid.dt)
    return float(np.sum(power_t_w) * dt_fs)


def wavelength_axis_nm(pulse: PulseState) -> np.ndarray:
    # pulse.grid.w is angular-frequency offset (rad/fs) around center frequency.
    omega_offset_rad_per_fs = np.asarray(pulse.grid.w, dtype=float)
    lambda0_nm = float(pulse.grid.center_wavelength_nm)
    omega0_rad_per_fs = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / lambda0_nm
    omega_abs_rad_per_fs = omega0_rad_per_fs + omega_offset_rad_per_fs

    lam_nm = np.full_like(omega_abs_rad_per_fs, np.nan, dtype=float)
    positive = omega_abs_rad_per_fs > 0.0
    lam_nm[positive] = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / omega_abs_rad_per_fs[positive]
    return lam_nm


def spectrum_power(pulse: PulseState) -> np.ndarray:
    spectrum = np.asarray(pulse.spectrum_w, dtype=float)
    if spectrum.size and np.any(np.isfinite(spectrum)):
        return spectrum

    field_t = np.asarray(pulse.field_t, dtype=np.complex128)
    aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    return np.abs(aw) ** 2


def blue_band_peak_ratio(lam_nm: np.ndarray, power: np.ndarray) -> float:
    finite = np.isfinite(lam_nm) & np.isfinite(power)
    blue = finite & (lam_nm >= 500.0) & (lam_nm <= 650.0)
    if not np.any(blue):
        raise ValueError("Blue-band wavelength mask [500, 650] nm is empty or non-finite.")

    total_peak = float(np.nanmax(power[finite]))
    blue_peak = float(np.nanmax(power[blue]))
    return blue_peak / total_peak


@pytest.mark.physics
@pytest.mark.gnlse
def test_fiber_high_order_dispersion_raman_and_shock_yield_blue_dispersive_wave_peak() -> None:
    gnlse = pytest.importorskip("gnlse")
    del gnlse

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
                            "n_samples": 4096,
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
            physics=FiberPhysicsCfg(
                length_m=0.15,
                gamma_1_per_w_m=0.11,
                self_steepening=True,
                dispersion=DispersionTaylorCfg(
                    betas_psn_per_m=[
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
                ),
                raman=RamanCfg(model="blowwood"),
            ),
            numerics=WustGnlseNumericsCfg(
                z_saves=200,
                method="RK45",
                rtol=1e-5,
                atol=1e-8,
                time_window_override_ps=12.5,
                keep_full_solution=False,
            ),
        )
    ).process(initial)

    final = result.state

    energy_in = compute_energy(initial.pulse)
    energy_out = compute_energy(final.pulse)
    energy_ratio = energy_out / energy_in if energy_in > 0 else float("nan")
    assert np.isfinite(energy_ratio) and 0.90 <= energy_ratio <= 1.10, (
        "Energy sanity check failed: expected finite energy_out/energy_in in [0.90, 1.10], "
        f"got {energy_ratio:.6g} (in={energy_in:.6g}, out={energy_out:.6g})."
    )

    lam_nm = wavelength_axis_nm(final.pulse)
    power_out = spectrum_power(final.pulse)
    blue_ratio = blue_band_peak_ratio(lam_nm, power_out)

    finite = np.isfinite(lam_nm) & np.isfinite(power_out)
    blue = finite & (lam_nm >= 500.0) & (lam_nm <= 650.0)
    blue_peak_wavelength_nm = float(lam_nm[blue][np.nanargmax(power_out[blue])])
    global_peak_wavelength_nm = float(lam_nm[finite][np.nanargmax(power_out[finite])])

    assert blue_ratio >= 1e-4, (
        "Dispersive-wave proxy failed: "
        f"blue_ratio={blue_ratio:.6g}, "
        f"blue_band_peak_wavelength_nm={blue_peak_wavelength_nm:.3f}, "
        f"global_peak_wavelength_nm={global_peak_wavelength_nm:.3f}."
    )

    artifact_dir = os.environ.get("CPA_SIM_ARTIFACT_DIR")
    if artifact_dir:
        try:
            if "MPLBACKEND" not in os.environ:
                os.environ["MPLBACKEND"] = "Agg"
            import matplotlib.pyplot as plt

            out_dir = Path(artifact_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            lam_in = wavelength_axis_nm(initial.pulse)
            power_in = spectrum_power(initial.pulse)

            mask_in = np.isfinite(lam_in) & np.isfinite(power_in)
            mask_out = np.isfinite(lam_nm) & np.isfinite(power_out)
            eps = 1e-30

            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.plot(lam_in[mask_in], np.log10(power_in[mask_in] + eps), label="z=0")
            ax.plot(lam_nm[mask_out], np.log10(power_out[mask_out] + eps), label="z=L")
            ax.axvline(blue_peak_wavelength_nm, linestyle="--", linewidth=1.0, color="tab:blue")
            ax.text(
                blue_peak_wavelength_nm,
                float(np.nanmax(np.log10(power_out[mask_out] + eps))),
                f" blue peak {blue_peak_wavelength_nm:.1f} nm",
                color="tab:blue",
                va="top",
            )
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel(r"$\\log_{10}(P_\\lambda)$ [a.u.]")
            ax.set_title("Dispersive-wave regression: blowwood Raman + self-steepening")
            ax.legend()
            ax.grid(alpha=0.3)

            fig.tight_layout()
            fig.savefig(out_dir / "dispersive_wave_blowwood.png", dpi=140)
            plt.close(fig)
        except Exception:
            # Artifact generation must never fail the physics regression itself.
            pass
