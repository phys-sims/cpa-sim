from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.integration
def test_cli_tune_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "cpa_sim.cli", "tune", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "usage: cpa-sim tune" in proc.stdout
    assert "run" in proc.stdout


@pytest.mark.integration
def test_cli_tune_run_placeholder_defaults_plots_off() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpa_sim.cli",
            "tune",
            "run",
            "--config",
            "tuning.yaml",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "cpa.emit_stage_plots=False" in proc.stdout
