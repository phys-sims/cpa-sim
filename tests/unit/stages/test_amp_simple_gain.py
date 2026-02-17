import pytest

from cpa_sim.models import AmpCfg, PipelineConfig
from cpa_sim.pipeline import run_pipeline


@pytest.mark.unit
def test_simple_gain_scales_amp_energy_metric() -> None:
    baseline = run_pipeline(PipelineConfig(amp=AmpCfg(gain_linear=1.0)))
    boosted = run_pipeline(PipelineConfig(amp=AmpCfg(gain_linear=4.0)))

    baseline_energy = baseline.metrics["cpa.amp.amp.energy_au"]
    boosted_energy = boosted.metrics["cpa.amp.amp.energy_au"]

    assert boosted_energy == pytest.approx(4.0 * baseline_energy)
    assert boosted.metrics["cpa.amp.amp.gain_linear"] == pytest.approx(4.0)
