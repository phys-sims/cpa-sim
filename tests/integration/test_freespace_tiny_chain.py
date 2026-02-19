import math

import pytest

from cpa_sim.models import (
    FiberCfg,
    MetricsCfg,
    PhaseOnlyDispersionCfg,
    PipelineConfig,
    SimpleGainCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.pipeline import run_pipeline


@pytest.mark.integration
def test_freespace_compressor_metrics_present_and_finite() -> None:
    cfg = PipelineConfig(
        stretcher=PhaseOnlyDispersionCfg(name="stretcher", gdd_fs2=5000.0, tod_fs3=0.0),
        fiber=FiberCfg(),
        amp=SimpleGainCfg(gain_linear=1.0),
        compressor=TreacyGratingPairCfg(name="compressor", apply_to_pulse=True),
        metrics=MetricsCfg(name="metrics"),
    )
    result = run_pipeline(cfg)

    for key in (
        "cpa.compressor.compressor.gdd_fs2",
        "cpa.compressor.compressor.tod_fs3",
        "cpa.compressor.compressor.omega0_rad_per_fs",
        "cpa.metrics.summary.energy_au",
    ):
        assert key in result.metrics
        assert math.isfinite(result.metrics[key])
