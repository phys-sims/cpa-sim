from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.gnlse
def test_examples_use_canonical_stage_plot_artifacts_and_no_local_plot_duplication() -> None:
    for script in (
        Path("src/cpa_sim/examples/simple_fiber_dispersion.py"),
        Path("src/cpa_sim/examples/fiber_amp_spm.py"),
        Path("src/cpa_sim/examples/wave_breaking_raman.py"),
    ):
        source = script.read_text(encoding="utf-8")
        assert "plot_line_series" not in source
