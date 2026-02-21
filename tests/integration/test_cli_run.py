from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


def _run_cli(
    *, config_path: Path, out_dir: Path, dump_state_npz: bool = False
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "cpa_sim.cli",
        "run",
        str(config_path),
        "--out",
        str(out_dir),
    ]
    if dump_state_npz:
        cmd.append("--dump-state-npz")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@pytest.mark.integration
def test_cli_run_writes_canonical_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "configs" / "examples" / "basic_cpa.yaml"
    out_dir = tmp_path / "out"

    proc = _run_cli(config_path=config_path, out_dir=out_dir)
    assert proc.returncode == 0, proc.stderr

    metrics = out_dir / "metrics.json"
    artifacts = out_dir / "artifacts.json"
    for path in [metrics, artifacts]:
        assert path.exists(), f"Missing expected output file: {path.name}"

    metrics_payload = json.loads(metrics.read_text(encoding="utf-8"))
    artifacts_payload = json.loads(artifacts.read_text(encoding="utf-8"))

    assert metrics_payload["schema_version"] == "cpa.metrics.v1"
    assert "cpa.metrics.summary.energy_au" in metrics_payload["overall"]
    assert "metrics" in metrics_payload["per_stage"]
    assert "energy_au" in metrics_payload["per_stage"]["metrics"]

    assert artifacts_payload["schema_version"] == "cpa.artifacts.v1"
    assert "paths" in artifacts_payload
    artifact_paths = artifacts_payload["paths"]
    assert isinstance(artifact_paths, dict)

    assert not (out_dir / "metrics_overall.json").exists()
    assert not (out_dir / "metrics_stages.json").exists()
    assert not (out_dir / "artifacts_index.json").exists()

    if "metrics.plot_time_intensity" in artifact_paths:
        assert Path(artifact_paths["metrics.plot_time_intensity"]).exists()
    if "metrics.plot_spectrum" in artifact_paths:
        assert Path(artifact_paths["metrics.plot_spectrum"]).exists()


@pytest.mark.integration
def test_cli_run_optionally_dumps_final_state_npz(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "configs" / "examples" / "basic_cpa.yaml"
    out_dir = tmp_path / "out"

    proc = _run_cli(config_path=config_path, out_dir=out_dir, dump_state_npz=True)
    assert proc.returncode == 0, proc.stderr

    state_dump = out_dir / "state_final.npz"
    assert state_dump.exists()

    with np.load(state_dump) as payload:
        for required in [
            "t",
            "w",
            "field_t_real",
            "field_t_imag",
            "field_w_real",
            "field_w_imag",
            "intensity_t",
            "spectrum_w",
            "meta_json",
            "metrics_json",
            "artifacts_json",
        ]:
            assert required in payload.files

    artifacts_payload = json.loads((out_dir / "artifacts.json").read_text(encoding="utf-8"))
    assert artifacts_payload["paths"]["run.state_dump_npz"].endswith("state_final.npz")
