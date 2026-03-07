from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.gnlse
def test_examples_use_canonical_stage_plot_artifacts_and_no_local_plot_duplication() -> None:
    for script in (
        Path("src/cpa_sim/examples/wust_gnlse_fiber_example.py"),
        Path("src/cpa_sim/examples/spm_after_fiber_amp.py"),
        Path("src/cpa_sim/examples/gnlse_dispersive_wave_showcase.py"),
    ):
        source = script.read_text(encoding="utf-8")
        assert "plot_line_series" not in source
