from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pytest
import yaml

from cpa_sim.models import PipelineConfig
from cpa_sim.models.state import PulseSpec
from cpa_sim.pipeline import run_pipeline
from cpa_sim.reporting import build_validation_report


def _example_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return sorted((repo_root / "configs" / "examples").glob("*.yaml"))


def _load_example_with_warnings(path: Path) -> tuple[PipelineConfig, list[warnings.WarningMessage]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg = PipelineConfig.model_validate(payload)
    return cfg, caught


EXAMPLE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "autocorr_input_demo.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["stretcher", "metrics"],
    },
    "basic_cpa.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["stretcher", "fiber", "amp", "compressor", "metrics"],
    },
    "gnlse_canonical.yaml": {
        "required_metrics": ["cpa.fiber.fiber.energy_out_au", "cpa.metrics.summary.energy_au"],
        "required_stages": ["fiber", "metrics"],
        "optional_dependency": "gnlse",
        "marks": ["gnlse"],
    },
    "legacy_amplitude_deprecated.yaml": {
        "required_metrics": ["cpa.metrics.summary.energy_au"],
        "required_stages": ["metrics"],
        "expected_warning": "PulseSpec.amplitude is deprecated",
    },
    "tracy_golden.yaml": {
        "required_metrics": ["cpa.canonical.canonical.gdd_fs2", "cpa.canonical.canonical.tod_fs3"],
        "required_stages": ["canonical", "metrics"],
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

    cfg, caught_warnings = _load_example_with_warnings(example_path)

    expected_warning = expectation.get("expected_warning")
    if expected_warning is None:
        assert not any(
            "PulseSpec.amplitude is deprecated" in str(w.message) for w in caught_warnings
        )
    else:
        assert any(expected_warning in str(w.message) for w in caught_warnings)

    result = run_pipeline(cfg)
    report = build_validation_report(cfg=cfg, result=result, artifacts=result.artifacts)

    assert result.state.pulse.field_t.size == cfg.laser_gen.spec.pulse.n_samples
    for metric_name in expectation["required_metrics"]:
        assert metric_name in result.metrics

    stage_names = {stage.stage for stage in report.stages}
    for stage_name in expectation["required_stages"]:
        assert stage_name in stage_names

    if expected_warning is not None:
        amplitude_schema = PulseSpec.model_json_schema()["properties"]["amplitude"]
        assert amplitude_schema["deprecated"] is True


@pytest.mark.integration
def test_example_expectations_cover_all_example_yaml_files() -> None:
    names_on_disk = {path.name for path in _example_paths()}
    assert names_on_disk == set(EXAMPLE_EXPECTATIONS)
