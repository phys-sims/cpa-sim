from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


def _load_example(name: str) -> PipelineConfig:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "configs" / "examples" / name
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return PipelineConfig.model_validate(payload)


@pytest.mark.integration
def test_basic_cpa_example_loads_and_runs() -> None:
    cfg = _load_example("basic_cpa.yaml")
    result = run_pipeline(cfg)

    assert result.state.pulse.field_t.size == cfg.laser_gen.spec.pulse.n_samples
    assert "cpa.metrics.summary.energy_au" in result.metrics


@pytest.mark.integration
def test_tracy_golden_example_loads_and_runs() -> None:
    cfg = _load_example("tracy_golden.yaml")
    result = run_pipeline(cfg)

    assert "cpa.canonical.canonical.gdd_fs2" in result.metrics
    assert "cpa.canonical.canonical.tod_fs3" in result.metrics


@pytest.mark.integration
@pytest.mark.gnlse
def test_gnlse_canonical_example_loads_and_runs_when_dependency_available() -> None:
    pytest.importorskip("gnlse")
    cfg = _load_example("gnlse_canonical.yaml")
    result = run_pipeline(cfg)

    assert "cpa.fiber.fiber.energy_out_au" in result.metrics
