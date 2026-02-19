import pytest

from cpa_sim.models import FiberCfg, PipelineConfig
from cpa_sim.pipeline import run_pipeline


@pytest.mark.physics
def test_fiber_b_integral_proxy_matches_configured_phase() -> None:
    nonlinear_phase_rad = 1.25
    result = run_pipeline(
        PipelineConfig(
            fiber=FiberCfg(
                numerics={"backend": "toy_phase", "nonlinear_phase_rad": nonlinear_phase_rad}
            )
        )
    )

    assert result.metrics["cpa.fiber.fiber.b_integral_proxy_rad"] == pytest.approx(
        nonlinear_phase_rad
    )
