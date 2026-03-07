from __future__ import annotations

from pathlib import Path

import pytest

from cpa_sim.examples import wust_gnlse_fiber_example


@pytest.mark.integration
def test_wust_docs_match_cli_and_artifact_names() -> None:
    doc = Path("docs/examples/wust-gnlse-fiber-example.md").read_text(encoding="utf-8")

    assert "--format svg" in doc
    assert "--format pdf" not in doc

    expected_time = f"{wust_gnlse_fiber_example.DEFAULT_STAGE_NAME}_time_intensity.svg"
    expected_spectrum = f"{wust_gnlse_fiber_example.DEFAULT_STAGE_NAME}_spectrum.svg"
    assert expected_time in doc
    assert expected_spectrum in doc


def test_wust_cli_only_advertises_svg_format() -> None:
    parser = wust_gnlse_fiber_example._build_parser()
    format_action = next(a for a in parser._actions if a.dest == "format")

    assert format_action.choices == ["svg"]
    assert format_action.default == "svg"


@pytest.mark.integration
def test_spm_summary_declared_fiber_length_matches_example_configuration() -> None:
    source = Path("src/cpa_sim/examples/spm_after_fiber_amp.py").read_text(encoding="utf-8")

    assert "length_m=14.0" in source
    assert '"fiber_length_m": 14.0' in source
