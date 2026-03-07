from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from cpa_sim.examples.fiber_amp_spm import run_example as run_fiber_amp_spm_example
from cpa_sim.examples.simple_fiber_dispersion import (
    run_example as run_simple_fiber_dispersion_example,
)

ExampleRunner = Callable[[Path], dict[str, Any]]
ArtifactExtractor = Callable[[dict[str, Any]], dict[str, Path]]


def _run_simple_fiber_dispersion(out_dir: Path) -> dict[str, Any]:
    return run_simple_fiber_dispersion_example(out_dir, plot_format="svg")


def _run_fiber_amp_spm(out_dir: Path) -> dict[str, Any]:
    return run_fiber_amp_spm_example(out_dir=out_dir)


def _extract_simple_fiber_dispersion_artifacts(outputs: dict[str, Any]) -> dict[str, Path]:
    return {
        "time_before_svg": Path(outputs["time_before_svg"]),
        "spectrum_before_svg": Path(outputs["spectrum_before_svg"]),
        "time_after_svg": Path(outputs["time_after_svg"]),
        "spectrum_after_svg": Path(outputs["spectrum_after_svg"]),
        "metrics_time_overlay_svg": Path(outputs["metrics_time_overlay_svg"]),
        "metrics_spectrum_overlay_svg": Path(outputs["metrics_spectrum_overlay_svg"]),
    }


def _extract_fiber_amp_spm_artifacts(outputs: dict[str, Any]) -> dict[str, Path]:
    artifacts = outputs["artifacts"]
    return {name: Path(path) for name, path in artifacts.items()}


@pytest.mark.integration
@pytest.mark.gnlse
@pytest.mark.parametrize(
    ("example_name", "runner", "artifact_schema", "artifact_extractor"),
    [
        (
            "simple_fiber_dispersion",
            _run_simple_fiber_dispersion,
            {
                "time_before_svg",
                "spectrum_before_svg",
                "time_after_svg",
                "spectrum_after_svg",
                "metrics_time_overlay_svg",
                "metrics_spectrum_overlay_svg",
            },
            _extract_simple_fiber_dispersion_artifacts,
        ),
        (
            "fiber_amp_spm",
            _run_fiber_amp_spm,
            {
                "time_intensity_svg",
                "spectrum_svg",
                "metrics_time_overlay_svg",
                "metrics_spectrum_overlay_svg",
            },
            _extract_fiber_amp_spm_artifacts,
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
