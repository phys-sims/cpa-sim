import json
from pathlib import Path

import pytest

from cpa_sim.examples.spm_after_fiber_amp import run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_spm_after_fiber_amp_example_writes_expected_summary_json(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    run_example(out_dir=tmp_path)

    summary_path = tmp_path / "summary.json"
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0

    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert set(payload) == {"inputs", "metrics", "artifacts"}
    assert set(payload["inputs"]) == {
        "shape",
        "width_fs",
        "avg_power_in_w",
        "avg_power_out_target_w",
        "rep_rate_ghz",
        "fiber_length_m",
        "n2_m2_per_w",
        "aeff_m2",
    }
    assert set(payload["artifacts"]) == {"time_intensity_svg", "spectrum_svg"}
