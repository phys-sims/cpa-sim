from __future__ import annotations

import numpy as np
import pytest

from cpa_sim.models import DispersionTaylorCfg, FiberCfg, FiberPhysicsCfg, WustGnlseNumericsCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage


@pytest.fixture
def gaussian_state() -> LaserState:
    t = np.linspace(-800.0, 800.0, 512)
    dt = float(t[1] - t[0])
    sigma = 100.0
    field_t = (5.0 * np.exp(-(t**2) / (2.0 * sigma**2))).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t.size, d=dt))
    return LaserState(
        pulse=PulseState(
            grid=PulseGrid(
                t=t.tolist(),
                w=w.tolist(),
                dt=dt,
                dw=float(w[1] - w[0]),
                center_wavelength_nm=1030.0,
            ),
            field_t=field_t,
            field_w=field_w,
            intensity_t=np.abs(field_t) ** 2,
            spectrum_w=np.abs(field_w) ** 2,
        ),
        beam=BeamState(radius_mm=1.0, m2=1.0),
    )


def _spectral_rms(state: LaserState) -> float:
    w = np.asarray(state.pulse.grid.w, dtype=float)
    weights = np.abs(np.asarray(state.pulse.field_w)) ** 2
    weights = weights / np.sum(weights)
    mean = float(np.sum(w * weights))
    var = float(np.sum(((w - mean) ** 2) * weights))
    return float(np.sqrt(max(var, 0.0)))


@pytest.mark.physics
@pytest.mark.gnlse
def test_wust_gnlse_canonical_spm_case_pins_summary_metrics(gaussian_state: LaserState) -> None:
    pytest.importorskip("gnlse")

    # Per-test tolerance block (canonical WUST-GNLSE SPM-focused run).
    tolerances = {
        "energy_ratio_min": 0.95,
        "energy_ratio_max": 1.05,
        "bandwidth_growth_min": 1.02,
        "phase_proxy_min": 0.15,
        "phase_proxy_max": 0.25,
    }

    pre_field = np.asarray(gaussian_state.pulse.field_t)
    pre_bandwidth = _spectral_rms(gaussian_state)

    result = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=0.5,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.02,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(z_saves=16, keep_full_solution=False),
        )
    ).process(gaussian_state)

    post_state = result.state
    post_bandwidth = _spectral_rms(post_state)
    energy_ratio = result.metrics["fiber.energy_ratio"]

    overlap = np.vdot(pre_field, np.asarray(post_state.pulse.field_t))
    phase_proxy = float(np.abs(np.angle(overlap)))

    assert tolerances["energy_ratio_min"] <= energy_ratio <= tolerances["energy_ratio_max"]
    assert (post_bandwidth / pre_bandwidth) >= tolerances["bandwidth_growth_min"]
    assert tolerances["phase_proxy_min"] <= phase_proxy <= tolerances["phase_proxy_max"]
