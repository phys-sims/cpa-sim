import pytest

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


@pytest.mark.integration
def test_tiny_chain_runs_and_emits_finite_metrics() -> None:
    cfg = PipelineConfig()
    result = run_pipeline(cfg)

    assert result.state.pulse.field_t.size == cfg.laser_gen.spec.pulse.n_samples
    for key in [
        "cpa.metrics.summary.energy_au",
        "cpa.metrics.summary.peak_intensity_au",
        "cpa.metrics.summary.fwhm_fs",
        "cpa.metrics.summary.bandwidth_rad_per_fs",
        "cpa.metrics.summary.amplification_ratio",
        "cpa.metrics.summary.temporal_shape_similarity",
        "cpa.metrics.summary.spectral_shape_similarity",
    ]:
        assert key in result.metrics
        assert result.metrics[key] == pytest.approx(result.metrics[key])
