import pytest

from cpa_sim.models import AmpCfg, FiberCfg, MetricsCfg, PipelineConfig, PhaseOnlyDispersionCfg
from cpa_sim.pipeline import build_pipeline, run_pipeline


@pytest.mark.integration
def test_pipeline_supports_arbitrary_stage_permutation() -> None:
    cfg = PipelineConfig(
        stages=[
            AmpCfg(name="pre_amp", gain_linear=1.1),
            FiberCfg(name="fiber_main"),
            PhaseOnlyDispersionCfg(name="post_fs", gdd_fs2=1500.0, tod_fs3=0.0),
        ],
        metrics=MetricsCfg(name="metrics"),
    )

    pipeline = build_pipeline(cfg)
    stage_names = [stage.name for stage in pipeline.stages]

    assert stage_names == ["laser_init", "pre_amp", "fiber_main", "post_fs", "metrics"]


@pytest.mark.integration
def test_pipeline_can_run_without_stretcher_and_compressor() -> None:
    cfg = PipelineConfig(
        stages=[
            FiberCfg(name="fiber_only"),
            AmpCfg(name="amp_only", gain_linear=1.0),
        ]
    )

    result = run_pipeline(cfg)

    assert result.state.pulse.field_t.size == cfg.laser_gen.spec.pulse.n_samples
    assert "cpa.fiber_only.fiber_only.b_integral_proxy_rad" in result.metrics
    assert "cpa.amp_only.amp_only.gain_linear" in result.metrics
    assert "cpa.metrics.summary.energy_au" in result.metrics


@pytest.mark.integration
def test_stage_plot_policy_emits_artifacts_for_all_stages(tmp_path) -> None:
    cfg = PipelineConfig(
        stages=[
            PhaseOnlyDispersionCfg(name="fs_a", gdd_fs2=500.0, tod_fs3=0.0),
            FiberCfg(name="fiber_a"),
            AmpCfg(name="amp_a", gain_linear=1.0),
        ]
    )

    result = run_pipeline(
        cfg,
        policy={"cpa.emit_stage_plots": True, "cpa.stage_plot_dir": str(tmp_path)},
    )

    expected_stages = ["laser_init", "fs_a", "fiber_a", "amp_a", "metrics"]
    for stage_name in expected_stages:
        for suffix in ("plot_time_intensity", "plot_spectrum"):
            key = f"{stage_name}.{suffix}"
            assert key in result.state.artifacts
            assert (tmp_path / f"{stage_name}_{suffix.split('_', 1)[1]}.svg").exists()
