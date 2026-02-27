import pytest

from cpa_sim.models import FiberAmpWrapCfg, PipelineConfig
from cpa_sim.pipeline import run_pipeline


@pytest.mark.unit
def test_fiber_amp_wrap_hits_target_average_power() -> None:
    target_power_w = 0.25
    result = run_pipeline(
        PipelineConfig(stages=[FiberAmpWrapCfg(name="amp", power_out_w=target_power_w)])
    )

    assert result.metrics["cpa.amp.amp.power_out_avg_w"] == pytest.approx(target_power_w, rel=2e-3)


@pytest.mark.unit
def test_fiber_amp_wrap_requires_positive_power_out_w() -> None:
    with pytest.raises(ValueError, match="power_out_w"):
        FiberAmpWrapCfg(power_out_w=0.0)
