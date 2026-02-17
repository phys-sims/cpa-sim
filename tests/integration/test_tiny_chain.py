import pytest

from cpa_sim.models import AmpCfg, FiberCfg, FreeSpaceCfg, PipelineConfig, StageRef
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
    ]:
        assert key in result.metrics
        assert result.metrics[key] == pytest.approx(result.metrics[key])


@pytest.mark.integration
def test_chain_without_stretcher_and_with_multiple_fiber_amp_pairs() -> None:
    cfg = PipelineConfig(
        free_space_stages={"compressor_only": FreeSpaceCfg(name="compressor_only", gdd_fs2=-100.0)},
        fiber_stages={
            "fiber_a": FiberCfg(name="fiber_a", nonlinear_phase_rad=0.6),
            "fiber_b": FiberCfg(name="fiber_b", nonlinear_phase_rad=0.2),
        },
        amp_stages={
            "amp_a": AmpCfg(name="amp_a", gain_linear=1.5),
            "amp_b": AmpCfg(name="amp_b", gain_linear=1.2),
        },
        stage_chain=[
            StageRef(stage_type="laser_gen", key="laser_init"),
            StageRef(stage_type="fiber", key="fiber_a"),
            StageRef(stage_type="amp", key="amp_a"),
            StageRef(stage_type="fiber", key="fiber_b"),
            StageRef(stage_type="amp", key="amp_b"),
            StageRef(stage_type="free_space", key="compressor_only"),
            StageRef(stage_type="metrics", key="metrics"),
        ],
    )

    result = run_pipeline(cfg)

    assert "cpa.fiber_a.fiber_a.b_integral_proxy_rad" in result.metrics
    assert "cpa.amp_b.amp_b.gain_linear" in result.metrics
    assert "cpa.compressor_only.compressor_only.gdd_fs2" in result.metrics
