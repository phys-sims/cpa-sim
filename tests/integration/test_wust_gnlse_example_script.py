from pathlib import Path

import pytest

from cpa_sim.examples.wust_gnlse_fiber_example import DEFAULT_STAGE_NAME, run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_wust_gnlse_example_stage_naming_contract(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    outputs = run_example(tmp_path, plot_format="svg")

    assert outputs["time_before"].name == "laser_init_time_intensity.svg"
    assert outputs["spectrum_before"].name == "laser_init_spectrum.svg"
    assert outputs["time_after"].name == f"{DEFAULT_STAGE_NAME}_time_intensity.svg"
    assert outputs["spectrum_after"].name == f"{DEFAULT_STAGE_NAME}_spectrum.svg"
    assert outputs["time"] == outputs["time_after"]
    assert outputs["spectrum"] == outputs["spectrum_after"]
