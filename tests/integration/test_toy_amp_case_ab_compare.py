from pathlib import Path
from subprocess import run

import pytest


@pytest.mark.integration
def test_toy_amp_case_ab_comparison_writes_outputs(tmp_path: Path) -> None:
    result = run(
        [
            "python",
            "scripts/examples/toy_amp_case_ab_compare.py",
            "--out",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    comparison_path = tmp_path / "comparison_summary.json"
    case_a_summary = tmp_path / "case-a" / "run_summary.json"
    case_b_summary = tmp_path / "case-b" / "run_summary.json"

    assert comparison_path.exists()
    assert case_a_summary.exists()
    assert case_b_summary.exists()
