import json
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

    comparison = json.loads(comparison_path.read_text())
    case_a = comparison["cases"]["A_direct"]
    case_b = comparison["cases"]["B_cpa"]

    assert comparison["shared_amp"]["amp_power_w"] == pytest.approx(5.0)

    assert (
        comparison["laser_gen"]["shared_spec"]["name"]
        == "laser_init_pritel_uoc_1550_ultrafast_optical_clock"
    )
    assert comparison["laser_gen"]["shared_spec"]["center_wavelength_nm"] == pytest.approx(1550.0)

    assert comparison["catalog"]["laser"] == "pritel_uoc_1550_ultrafast_optical_clock"
    assert comparison["catalog"]["amp"] == "calmar_coronado_benchtop_edfa_1550"

    assert case_a["comparison_metrics"]["power_out_avg_w"] == pytest.approx(5.0, rel=2e-3)
    assert case_b["comparison_metrics"]["power_out_avg_w"] == pytest.approx(5.0, rel=2e-3)

    for metric_name in (
        "energy_in_au",
        "energy_out_au",
        "power_in_avg_w",
        "power_out_avg_w",
        "peak_power_in_w",
        "peak_power_out_w",
        "pipeline.final_energy_au",
        "pipeline.final_peak_power_au",
    ):
        assert case_a["comparison_metrics"][metric_name] is not None
        assert case_b["comparison_metrics"][metric_name] is not None
