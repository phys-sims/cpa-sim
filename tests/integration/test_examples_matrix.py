from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from cpa_sim.examples.spm_after_fiber_amp import run_example as run_spm_example
from cpa_sim.examples.wust_gnlse_fiber_example import run_example as run_wust_example

ExampleRunner = Callable[[Path], dict[str, Any]]
ArtifactExtractor = Callable[[dict[str, Any]], dict[str, Path]]


def _run_wust(out_dir: Path) -> dict[str, Any]:
    return run_wust_example(out_dir, plot_format="svg")


def _run_spm(out_dir: Path) -> dict[str, Any]:
    return run_spm_example(out_dir=out_dir)


def _extract_wust_artifacts(outputs: dict[str, Any]) -> dict[str, Path]:
    return {name: Path(path) for name, path in outputs.items()}


def _extract_spm_artifacts(outputs: dict[str, Any]) -> dict[str, Path]:
    artifacts = outputs["artifacts"]
    return {name: Path(path) for name, path in artifacts.items()}


@pytest.mark.integration
@pytest.mark.gnlse
@pytest.mark.parametrize(
    ("example_name", "runner", "artifact_schema", "artifact_extractor"),
    [
        (
            "wust_gnlse_fiber_example",
            _run_wust,
            {"time", "spectrum"},
            _extract_wust_artifacts,
        ),
        (
            "spm_after_fiber_amp",
            _run_spm,
            {"time_intensity_svg", "spectrum_svg"},
            _extract_spm_artifacts,
        ),
    ],
)
def test_examples_artifact_matrix(
    tmp_path: Path,
    example_name: str,
    runner: ExampleRunner,
    artifact_schema: set[str],
    artifact_extractor: ArtifactExtractor,
) -> None:
    pytest.importorskip("gnlse")

    outputs = runner(tmp_path / example_name)
    artifacts = artifact_extractor(outputs)

    assert set(artifacts) == artifact_schema
    for artifact in artifacts.values():
        assert artifact.exists()
        assert artifact.stat().st_size > 0
        assert "<svg" in artifact.read_text(encoding="utf-8")
