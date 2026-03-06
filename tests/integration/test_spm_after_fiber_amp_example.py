from pathlib import Path

import pytest

from cpa_sim.examples.spm_after_fiber_amp import run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_spm_after_fiber_amp_example_generates_svg_outputs(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    outputs = run_example(out_dir=tmp_path)

    summary_path = tmp_path / "summary.json"
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0

    for path in outputs["artifacts"].values():
        artifact = Path(path)
        assert artifact.exists()
        assert artifact.stat().st_size > 0
        assert "<svg" in artifact.read_text(encoding="utf-8")

    assert outputs["plot_policy_overrides"] == {
        "cpa.plot.line.threshold_fraction": 1e-2,
    }
