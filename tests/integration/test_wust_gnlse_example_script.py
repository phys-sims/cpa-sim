from pathlib import Path

import pytest

from scripts.examples.wust_gnlse_fiber_example import run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_wust_gnlse_example_script_generates_svg_outputs(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    outputs = run_example(tmp_path, plot_format="svg")

    for path in outputs.values():
        assert path.exists()
        assert path.stat().st_size > 0
        assert "<svg" in path.read_text(encoding="utf-8")
