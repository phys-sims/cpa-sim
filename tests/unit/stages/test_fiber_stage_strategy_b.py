import sys
import types

import numpy as np
import pytest

from cpa_sim.models import (
    DispersionInterpolationCfg,
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    RamanCfg,
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


class _FakeSolution:
    def __init__(self, field_t: np.ndarray):
        self.At = np.vstack([field_t, 1.1 * field_t])


class _FakeGNLSE:
    def __init__(self, setup: object):
        self.setup = setup

    def run(self) -> _FakeSolution:
        return _FakeSolution(self.setup.pulse_model)


@pytest.fixture
def fake_gnlse_module() -> types.ModuleType:
    mod = types.ModuleType("gnlse")

    class GNLSESetup:
        pass

    def dispersion_taylor(loss: float, betas: list[float]) -> tuple[str, float, list[float]]:
        return ("taylor", loss, betas)

    def dispersion_interp(
        loss: float,
        center_wl_nm: float,
        lambdas_nm: list[float],
        neff: list[float],
    ) -> tuple[str, float, float, list[float], list[float]]:
        return ("interp", loss, center_wl_nm, lambdas_nm, neff)

    mod.GNLSESetup = GNLSESetup
    mod.DispersionFiberFromTaylor = dispersion_taylor
    mod.DispersionFiberFromInterpolation = dispersion_interp
    mod.GNLSE = _FakeGNLSE
    mod.raman_blowwood = object()
    return mod


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
def test_wust_backend_missing_dependency_has_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import cpa_sim.stages.fiber.backends.wust_gnlse as wust_backend

    monkeypatch.setattr(
        wust_backend,
        "_import_gnlse",
        lambda: (_ for _ in ()).throw(
            RuntimeError("Fiber backend 'wust_gnlse' requires the optional 'gnlse' package.")
        ),
    )
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


@pytest.mark.unit
def test_units_helpers_roundtrip_scalars() -> None:
    from cpa_sim.stages.fiber.utils.units import fs_to_ps, m_to_nm, nm_to_m, ps_to_fs

    assert fs_to_ps(2500.0) == pytest.approx(2.5)
    assert ps_to_fs(1.75) == pytest.approx(1750.0)
    assert nm_to_m(1030.0) == pytest.approx(1.03e-6)
    assert m_to_nm(1.55e-6) == pytest.approx(1550.0)
    assert m_to_nm(nm_to_m(800.0)) == pytest.approx(800.0)


def test_wust_setup_fields_populated_with_expected_units(
    monkeypatch: pytest.MonkeyPatch, fake_gnlse_module: types.ModuleType
) -> None:
    monkeypatch.setitem(sys.modules, "gnlse", fake_gnlse_module)

    s = _state()
    stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                length_m=1.25,
                loss_db_per_m=0.1,
                gamma_1_per_w_m=0.002,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[-0.025, 0.001]),
                raman=RamanCfg(model="blowwood"),
                self_steepening=True,
            ),
            numerics=WustGnlseNumericsCfg(record_backend_version=False),
        )
    )

    result = stage.process(s)
    assert result.state.artifacts["fiber.backend"] == "wust_gnlse"
    assert result.state.artifacts["fiber.resolution"] == "64"
    assert float(result.state.artifacts["fiber.time_window_ps"]) == pytest.approx(0.002)
    assert result.state.meta["pulse"]["field_units"] == "sqrt(W)"
    assert result.state.metrics["fiber.grid_points"] == pytest.approx(64.0)


@pytest.mark.unit
def test_wust_interpolation_dispersion_mapping(
    monkeypatch: pytest.MonkeyPatch, fake_gnlse_module: types.ModuleType
) -> None:
    monkeypatch.setitem(sys.modules, "gnlse", fake_gnlse_module)
    s = _state()

    stage = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                gamma_1_per_w_m=0.001,
                dispersion=DispersionInterpolationCfg(
                    effective_indices=[1.44, 1.45],
                    lambdas_nm=[1000.0, 1060.0],
                    central_wavelength_nm=1030.0,
                ),
            ),
            numerics=WustGnlseNumericsCfg(record_backend_version=False),
        )
    )
    result = stage.process(s)
    assert result.state.metrics["fiber.energy_out_au"] > 0.0
