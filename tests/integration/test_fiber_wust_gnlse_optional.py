import numpy as np
import pytest

from cpa_sim.models import DispersionTaylorCfg, FiberCfg, FiberPhysicsCfg, WustGnlseNumericsCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage


def _requires_gnlse() -> None:
    pytest.importorskip("gnlse")


def _gaussian_state() -> LaserState:
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


def _rms_axis(values: np.ndarray, axis: np.ndarray) -> float:
    weights = np.abs(values) ** 2
    weights = weights / np.sum(weights)
    mean = np.sum(axis * weights)
    var = np.sum((axis - mean) ** 2 * weights)
    return float(np.sqrt(max(var, 0.0)))


@pytest.mark.integration
@pytest.mark.gnlse
def test_wust_gnlse_spm_only_preserves_energy_and_broadens_spectrum() -> None:
    _requires_gnlse()
    state = _gaussian_state()
    pre_energy = float(np.sum(np.abs(state.pulse.field_t) ** 2) * state.pulse.grid.dt)
    pre_rms_w = _rms_axis(state.pulse.field_w, np.asarray(state.pulse.grid.w, dtype=float))

    stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=0.2,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.01,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(z_saves=16, keep_full_solution=False),
        )
    )
    result = stage.process(state)

    post_energy = float(
        np.sum(np.abs(result.state.pulse.field_t) ** 2) * result.state.pulse.grid.dt
    )
    post_rms_w = _rms_axis(
        result.state.pulse.field_w, np.asarray(result.state.pulse.grid.w, dtype=float)
    )
    assert post_energy == pytest.approx(pre_energy, rel=5e-2)
    assert post_rms_w > pre_rms_w


@pytest.mark.integration
@pytest.mark.gnlse
def test_wust_gnlse_gvd_only_broadens_temporal_width() -> None:
    _requires_gnlse()
    state = _gaussian_state()
    pre_rms_t = _rms_axis(state.pulse.field_t, np.asarray(state.pulse.grid.t, dtype=float))

    stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=0.3,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.0,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.03]),
            ),
            numerics=WustGnlseNumericsCfg(z_saves=16, keep_full_solution=False),
        )
    )
    result = stage.process(state)

    post_rms_t = _rms_axis(
        result.state.pulse.field_t, np.asarray(result.state.pulse.grid.t, dtype=float)
    )
    assert post_rms_t > pre_rms_t


@pytest.mark.integration
@pytest.mark.gnlse
def test_wust_gnlse_raman_toggle_produces_finite_output() -> None:
    _requires_gnlse()
    state = _gaussian_state()

    stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=0.1,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.002,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
                raman={"kind": "wust", "model": "blowwood"},
            ),
            numerics=WustGnlseNumericsCfg(z_saves=8, keep_full_solution=False),
        )
    )
    result = stage.process(state)

    assert np.all(np.isfinite(result.state.pulse.intensity_t))
    assert np.all(np.isfinite(result.state.pulse.spectrum_w))
    assert np.isfinite(result.metrics["fiber.energy_out"])
