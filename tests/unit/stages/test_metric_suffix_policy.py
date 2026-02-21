from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    PhaseOnlyDispersionCfg,
    PipelineConfig,
    SimpleGainCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.pipeline import run_pipeline
from cpa_sim.stages.fiber import FiberStage

_DIMENSIONLESS_LEAF_KEYS = {
    "apply_to_pulse",
    "diffraction_order",
    "energy_ratio",
    "gain_linear",
    "grid_points",
    "n_passes",
}


def _leaf(metric_key: str) -> str:
    return metric_key.rsplit(".", 1)[-1]


def _has_unit_suffix(leaf_key: str) -> bool:
    suffixes = (
        "_au",
        "_j",
        "_w",
        "_fs",
        "_fs2",
        "_fs3",
        "_rad",
        "_rad_per_fs",
        "_deg",
        "_nm",
        "_um",
        "_lpmm",
        "_db",
        "_db_per_m",
        "_per_m",
    )
    return leaf_key.endswith(suffixes)


@pytest.mark.unit
def test_stage_metric_keys_follow_suffix_policy() -> None:
    result = run_pipeline(
        PipelineConfig(
            stretcher=PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=1.0, tod_fs3=0.0),
            fiber=FiberCfg(name="fiber"),
            amp=SimpleGainCfg(name="amp", gain_linear=1.1),
            stages=[],
        )
    )

    stage_prefixes = (
        "cpa.laser_init.",
        "cpa.stretcher.",
        "cpa.fiber.",
        "cpa.amp.",
    )
    stage_keys = [k for k in result.metrics if k.startswith(stage_prefixes)]
    assert stage_keys

    invalid = []
    for key in stage_keys:
        leaf = _leaf(key)
        if leaf in _DIMENSIONLESS_LEAF_KEYS:
            continue
        if not _has_unit_suffix(leaf):
            invalid.append(key)

    assert not invalid, f"Found stage metrics missing explicit unit suffixes: {invalid}"


class _FakeSolution:
    def __init__(self, field_t: np.ndarray):
        self.At = np.vstack([field_t, field_t])


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

    mod.GNLSESetup = GNLSESetup
    mod.DispersionFiberFromTaylor = dispersion_taylor
    mod.GNLSE = _FakeGNLSE
    return mod


def _state() -> LaserState:
    t = np.linspace(-1.0, 1.0, 64)
    dt = float(t[1] - t[0])
    field_t = np.exp(-(t**2)).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    return LaserState(
        pulse=PulseState(
            grid=PulseGrid(
                t=t.tolist(),
                w=np.linspace(-4.0, 4.0, 64).tolist(),
                dt=dt,
                dw=1.0,
                center_wavelength_nm=1030.0,
            ),
            field_t=field_t,
            field_w=field_w,
            intensity_t=np.abs(field_t) ** 2,
            spectrum_w=np.abs(field_w) ** 2,
        ),
        beam=BeamState(radius_mm=1.0, m2=1.0),
    )


@pytest.mark.unit
def test_wust_energy_metrics_use_explicit_units_and_fs_to_s_conversion(
    monkeypatch: pytest.MonkeyPatch, fake_gnlse_module: types.ModuleType
) -> None:
    monkeypatch.setitem(sys.modules, "gnlse", fake_gnlse_module)

    result = FiberStage(
        FiberCfg(
            physics=FiberPhysicsCfg(
                gamma_1_per_w_m=0.001,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(record_backend_version=False),
        )
    ).process(_state())

    metrics = result.metrics
    assert "fiber.energy_in_au" in metrics
    assert "fiber.energy_out_au" in metrics
    assert "fiber.energy_in_j" in metrics
    assert "fiber.energy_out_j" in metrics
    assert "fiber.spectral_rms_au" in metrics
    assert metrics["fiber.energy_in_j"] == pytest.approx(metrics["fiber.energy_in_au"] * 1e-15)
    assert metrics["fiber.energy_out_j"] == pytest.approx(metrics["fiber.energy_out_au"] * 1e-15)
