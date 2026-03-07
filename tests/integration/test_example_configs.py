from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline
from cpa_sim.reporting import build_validation_report


def _example_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return sorted((repo_root / "configs" / "examples").glob("*.yaml"))


def _load_example(path: Path) -> PipelineConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PipelineConfig.model_validate(payload)


EXAMPLE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "simple_fiber_dispersion.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["simple_fiber_dispersion", "metrics"],
        "optional_dependency": "gnlse",
        "marks": ["gnlse"],
    },
    "wave_breaking_raman.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["wave_breaking_raman", "metrics"],
        "optional_dependency": "gnlse",
        "marks": ["gnlse"],
    },
    "fiber_amp_spm.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["fiber_amp_spm", "metrics"],
        "optional_dependency": "gnlse",
        "marks": ["gnlse"],
    },
    "treacy_stage_validation.yaml": {
        "required_metrics": [
            "cpa.treacy_validation.treacy_validation.gdd_fs2",
            "cpa.treacy_validation.treacy_validation.tod_fs3",
        ],
        "required_stages": ["treacy_validation", "metrics"],
    },
    "end_to_end_1560nm.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": [
            "fiber_regular_disp_1560nm",
            "fiber_amp_spm",
            "treacy_compressor",
            "metrics",
        ],
        "optional_dependency": "gnlse",
        "marks": ["gnlse"],
    },
}


@pytest.mark.integration
@pytest.mark.parametrize(
    "example_path",
    [
        pytest.param(
            path,
            marks=tuple(
                getattr(pytest.mark, mark_name)
                for mark_name in EXAMPLE_EXPECTATIONS[path.name].get("marks", [])
            ),
            id=path.name,
        )
        for path in _example_paths()
    ],
)
def test_example_configs_load_and_run_with_expected_outputs(example_path: Path) -> None:
    expectation = EXAMPLE_EXPECTATIONS[example_path.name]
    optional_dependency = expectation.get("optional_dependency")
    if optional_dependency is not None:
        pytest.importorskip(optional_dependency)

    cfg = _load_example(example_path)

    result = run_pipeline(cfg)
    report = build_validation_report(cfg=cfg, result=result, artifacts=result.artifacts)

    assert result.state.pulse.field_t.size == cfg.laser_gen.spec.pulse.n_samples
    for metric_name in expectation["required_metrics"]:
        assert metric_name in result.metrics

    stage_names = {stage.stage for stage in report.stages}
    for stage_name in expectation["required_stages"]:
        assert stage_name in stage_names


@pytest.mark.integration
def test_example_expectations_cover_all_example_yaml_files() -> None:
    names_on_disk = {path.name for path in _example_paths()}
    assert names_on_disk == set(EXAMPLE_EXPECTATIONS)
