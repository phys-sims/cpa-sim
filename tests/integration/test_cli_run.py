from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_cli_run_writes_expected_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "configs" / "examples" / "basic_cpa.yaml"
    out_dir = tmp_path / "out"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpa_sim.cli",
            "run",
            str(config_path),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr

    overall = out_dir / "metrics_overall.json"
    stages = out_dir / "metrics_stages.json"
    artifacts = out_dir / "artifacts_index.json"

    assert overall.exists()
    assert stages.exists()
    assert artifacts.exists()

    overall_payload = json.loads(overall.read_text(encoding="utf-8"))
    stage_payload = json.loads(stages.read_text(encoding="utf-8"))

    assert "cpa.metrics.summary.energy_au" in overall_payload
    assert "metrics" in stage_payload
    assert "energy_au" in stage_payload["metrics"]
