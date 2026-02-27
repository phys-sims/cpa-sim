import numpy as np
import pytest

from cpa_sim.models import FiberAmpWrapCfg, PipelineConfig
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.pipeline import run_pipeline
from cpa_sim.stages.amp.fiber_amp_wrap import FiberAmpWrapStage


@pytest.mark.unit
def test_fiber_amp_wrap_reports_wrapper_metrics() -> None:
    target_power_w = 0.25
    result = run_pipeline(
        PipelineConfig(stages=[FiberAmpWrapCfg(name="amp", power_out_w=target_power_w)])
    )

    assert result.metrics["cpa.amp.amp.power_out_target_w"] == pytest.approx(target_power_w)
    assert result.metrics["cpa.amp.amp.power_in_avg_w"] > 0.0
    assert result.metrics["cpa.amp.amp.energy_in_j"] > 0.0
    assert result.metrics["cpa.amp.amp.energy_out_j"] > 0.0


@pytest.mark.unit
def test_fiber_amp_wrap_requires_positive_power_out_w() -> None:
    with pytest.raises(ValueError, match="power_out_w"):
        FiberAmpWrapCfg(power_out_w=0.0)


@pytest.mark.unit
def test_fiber_amp_wrap_requires_rep_rate_meta() -> None:
    stage = FiberAmpWrapStage(FiberAmpWrapCfg(power_out_w=1.0))
    state = _state(rep_rate_mhz=None)
    with pytest.raises(ValueError, match="rep_rate_mhz"):
        stage.process(state)


@pytest.mark.unit
def test_fiber_amp_wrap_requires_positive_input_power() -> None:
    stage = FiberAmpWrapStage(FiberAmpWrapCfg(power_out_w=1.0))
    state = _state(rep_rate_mhz=1.0, zero_field=True)
    with pytest.raises(ValueError, match="normalization/windowing"):
        stage.process(state)


def _state(*, rep_rate_mhz: float | None, zero_field: bool = False) -> LaserState:
    t = np.linspace(-1.0, 1.0, 64)
    field_t = (
        np.zeros_like(t, dtype=np.complex128)
        if zero_field
        else np.exp(-(t**2)).astype(np.complex128)
    )
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    meta = {} if rep_rate_mhz is None else {"rep_rate_mhz": rep_rate_mhz}
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
        meta=meta,
    )
