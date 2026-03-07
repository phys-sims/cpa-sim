import json
from pathlib import Path

import pytest

from cpa_sim.examples.end_to_end_1560nm import run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_end_to_end_1560nm_example_writes_summary_and_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    out_dir = tmp_path / "out"
    plot_dir = out_dir / "stage-plots"
    payload = run_example(out_dir=out_dir, plot_dir=plot_dir, seed=1560, ci_safe=True)

    summary_path = out_dir / "run_summary.json"
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0

    parsed = json.loads(summary_path.read_text(encoding="utf-8"))
    assert parsed["seed"] == 1560
    assert parsed["ci_safe"] is True
    assert "cpa.metrics.summary.energy_au" in parsed["metrics"]
    assert parsed["artifacts"]

    # Contract: caller gets the same summary payload that was persisted.
    assert payload == parsed
