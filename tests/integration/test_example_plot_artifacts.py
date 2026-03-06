from pathlib import Path

import pytest

from cpa_sim.examples.spm_after_fiber_amp import run_example as run_spm_example
from cpa_sim.examples.wust_gnlse_fiber_example import run_example as run_wust_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_examples_use_canonical_stage_plot_artifacts_and_no_local_plot_duplication(
    tmp_path: Path,
) -> None:
    pytest.importorskip("gnlse")

    wust_out = run_wust_example(tmp_path / "wust")
    assert set(wust_out) == {"time", "spectrum"}
    for artifact in wust_out.values():
        assert artifact.exists()
        assert artifact.name in {"fiber_example_time_intensity.svg", "fiber_example_spectrum.svg"}

    spm_out = run_spm_example(out_dir=tmp_path / "spm")
    assert set(spm_out["artifacts"]) == {"time_intensity_svg", "spectrum_svg"}
    assert spm_out["artifacts"]["time_intensity_svg"].endswith("fiber_amp_spm_time_intensity.svg")
    assert spm_out["artifacts"]["spectrum_svg"].endswith("fiber_amp_spm_spectrum.svg")

    for script in (
        Path("src/cpa_sim/examples/wust_gnlse_fiber_example.py"),
        Path("src/cpa_sim/examples/spm_after_fiber_amp.py"),
        Path("src/cpa_sim/examples/gnlse_dispersive_wave_showcase.py"),
    ):
        source = script.read_text(encoding="utf-8")
        assert "plot_line_series" not in source
