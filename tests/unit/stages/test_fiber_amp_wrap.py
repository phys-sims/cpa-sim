import numpy as np
import pytest

from cpa_sim.models import FiberAmpWrapCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.stages.amp.fiber_amp_wrap import FiberAmpWrapStage
from cpa_sim.stages.fiber import FiberStage

_FS_TO_S = 1e-15


def _pulse_energy_j(state: LaserState) -> float:
    intensity = np.abs(np.asarray(state.pulse.field_t, dtype=np.complex128)) ** 2
    return float(np.sum(intensity) * float(state.pulse.grid.dt) * _FS_TO_S)


def _power_avg_w(state: LaserState) -> float:
    rep_rate_hz = float(state.meta["rep_rate_mhz"]) * 1e6
    return _pulse_energy_j(state) * rep_rate_hz


def _gaussian_state(*, rep_rate_mhz: float | None = 2.0, amplitude: float = 1.0) -> LaserState:
    t = np.linspace(-300.0, 300.0, 256)
    dt = float(t[1] - t[0])
    sigma = 80.0
    field_t = (amplitude * np.exp(-(t**2) / (2.0 * sigma**2))).astype(np.complex128)
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t.size, d=dt))
    meta: dict[str, float] = {}
    if rep_rate_mhz is not None:
        meta["rep_rate_mhz"] = rep_rate_mhz
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
        meta=meta,
    )


def _install_fiber_stub(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def _stub_process(
        self: FiberStage, state: LaserState, *, policy=None
    ) -> StageResult[LaserState]:
        captured["cfg"] = self.cfg
        loss_total_db_per_m = float(self.cfg.physics.loss_db_per_m)
        length_m = float(self.cfg.physics.length_m)
        power_ratio = float(10.0 ** (-(loss_total_db_per_m * length_m) / 10.0))
        field_scale = float(np.sqrt(power_ratio))

        updated = state.deepcopy()
        updated.pulse.field_t = updated.pulse.field_t * field_scale
        updated.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(updated.pulse.field_t)))
        updated.pulse.intensity_t = np.abs(updated.pulse.field_t) ** 2
        updated.pulse.spectrum_w = np.abs(updated.pulse.field_w) ** 2
        return StageResult(state=updated, metrics={})

    monkeypatch.setattr(FiberStage, "process", _stub_process)
    return captured


@pytest.mark.unit
def test_fiber_amp_wrap_hits_target_power_without_intrinsic_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_fiber_stub(monkeypatch)
    state = _gaussian_state(rep_rate_mhz=2.0)
    power_in_avg_w = _power_avg_w(state)
    target_power_w = 2.5 * power_in_avg_w

    stage = FiberAmpWrapStage(
        FiberAmpWrapCfg(
            power_out_w=target_power_w,
            physics={"length_m": 1.4, "loss_db_per_m": 0.0},
        )
    )
    result = stage.process(state)

    wrapped_cfg = captured["cfg"]
    assert float(wrapped_cfg.physics.loss_db_per_m) == pytest.approx(
        result.metrics["amp.derived_loss_total_db_per_m"],
        rel=0.0,
        abs=1e-12,
    )
    assert result.metrics["amp.power_out_avg_w"] == pytest.approx(target_power_w, rel=1e-12)


@pytest.mark.unit
def test_fiber_amp_wrap_hits_target_power_with_intrinsic_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_fiber_stub(monkeypatch)
    state = _gaussian_state(rep_rate_mhz=5.0)
    power_in_avg_w = _power_avg_w(state)
    target_power_w = 0.4 * power_in_avg_w
    intrinsic_loss_db_per_m = 0.8
    length_m = 2.0

    stage = FiberAmpWrapStage(
        FiberAmpWrapCfg(
            power_out_w=target_power_w,
            physics={"length_m": length_m, "loss_db_per_m": intrinsic_loss_db_per_m},
        )
    )
    result = stage.process(state)

    loss_eff_db_per_m = result.metrics["amp.derived_loss_eff_db_per_m"]
    loss_total_db_per_m = result.metrics["amp.derived_loss_total_db_per_m"]
    assert loss_total_db_per_m == pytest.approx(
        intrinsic_loss_db_per_m + loss_eff_db_per_m,
        rel=0.0,
        abs=1e-12,
    )
    wrapped_cfg = captured["cfg"]
    assert float(wrapped_cfg.physics.loss_db_per_m) == pytest.approx(loss_total_db_per_m)
    assert result.metrics["amp.power_out_avg_w"] == pytest.approx(target_power_w, rel=1e-12)


@pytest.mark.unit
def test_fiber_amp_wrap_rejects_missing_rep_rate_mhz() -> None:
    stage = FiberAmpWrapStage(FiberAmpWrapCfg(power_out_w=1.0))
    with pytest.raises(ValueError, match="rep_rate_mhz"):
        stage.process(_gaussian_state(rep_rate_mhz=None))


@pytest.mark.unit
def test_fiber_amp_wrap_rejects_non_positive_input_power() -> None:
    stage = FiberAmpWrapStage(FiberAmpWrapCfg(power_out_w=1.0))
    with pytest.raises(ValueError, match="positive input average power"):
        stage.process(_gaussian_state(rep_rate_mhz=1.0, amplitude=0.0))
