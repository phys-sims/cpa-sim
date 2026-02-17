import numpy as np
import pytest

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    ToyPhaseNumericsCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.fiber import FiberStage
from cpa_sim.stages.fiber.utils.grid import resample_complex_uniform


def _state() -> LaserState:
    t = np.linspace(-1.0, 1.0, 64)
    field_t = np.exp(-(t**2)).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    return LaserState(
        pulse=PulseState(
            grid=PulseGrid(
                t=t.tolist(),
                w=np.linspace(-4.0, 4.0, 64).tolist(),
                dt=float(t[1] - t[0]),
                dw=1.0,
                center_wavelength_nm=1030.0,
            ),
            field_t=field_t,
            field_w=field_w,
            intensity_t=np.abs(field_t) ** 2,
            spectrum_w=np.abs(field_w) ** 2,
        ),
        beam=BeamState(radius_mm=1.2, m2=1.3),
    )


@pytest.mark.unit
def test_fiber_cfg_discriminator_variants_parse() -> None:
    cfg = FiberCfg(
        physics=FiberPhysicsCfg(dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.1, 0.0])),
        numerics={"backend": "wust_gnlse", "z_saves": 8},
    )
    assert isinstance(cfg.numerics, WustGnlseNumericsCfg)


@pytest.mark.unit
def test_fiber_cfg_missing_dispersion_fails_cleanly() -> None:
    with pytest.raises(Exception):
        FiberCfg(physics={"length_m": 1.0, "dispersion": {"kind": "taylor"}})


@pytest.mark.unit
def test_toy_phase_backend_preserves_beam_state() -> None:
    stage = FiberStage(FiberCfg(numerics=ToyPhaseNumericsCfg(nonlinear_phase_rad=0.2)))
    result = stage.process(_state())
    assert result.state.beam.radius_mm == pytest.approx(1.2)
    assert result.state.beam.m2 == pytest.approx(1.3)


@pytest.mark.unit
def test_non_uniform_grid_raises() -> None:
    s = _state()
    t = np.asarray(s.pulse.grid.t)
    t[4] += 1e-2
    s.pulse.grid = s.pulse.grid.model_copy(update={"t": t.tolist()})
    stage = FiberStage(FiberCfg())
    with pytest.raises(ValueError, match="uniformly spaced"):
        stage.process(s)


@pytest.mark.unit
def test_resampling_happens_only_when_policy_allows() -> None:
    s = _state()
    toy_result = FiberStage(FiberCfg()).process(s)
    assert toy_result.state.pulse.field_t.size == s.pulse.field_t.size

    signal = resample_complex_uniform(s.pulse.field_t, np.asarray(s.pulse.grid.t), 32)
    assert signal.size == 32


@pytest.mark.unit
def test_wust_backend_missing_dependency_has_clear_error() -> None:
    s = _state()
    stage = FiberStage(
        FiberCfg(
            numerics=WustGnlseNumericsCfg(
                grid_policy="force_resolution", resolution_override=32, record_backend_version=False
            )
        )
    )
    with pytest.raises(RuntimeError, match="optional 'gnlse'"):
        stage.process(s)
