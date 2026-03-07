from pathlib import Path

import pytest

from cpa_sim.examples.simple_fiber_dispersion import DEFAULT_STAGE_NAME, run_example


@pytest.mark.integration
@pytest.mark.gnlse
def test_simple_fiber_dispersion_stage_naming_contract(tmp_path: Path) -> None:
    pytest.importorskip("gnlse")

    outputs = run_example(tmp_path, plot_format="svg")

    assert outputs["time_before_svg"].name == "laser_init_time_intensity.svg"
    assert outputs["spectrum_before_svg"].name == "laser_init_spectrum.svg"
    assert outputs["time_after_svg"].name == f"{DEFAULT_STAGE_NAME}_time_intensity.svg"
    assert outputs["spectrum_after_svg"].name == f"{DEFAULT_STAGE_NAME}_spectrum.svg"
