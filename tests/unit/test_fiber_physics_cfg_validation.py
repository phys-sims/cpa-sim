import pytest
from pydantic import ValidationError

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberAmpWrapCfg,
    FiberPhysicsCfg,
    ToyPhaseNumericsCfg,
)


def test_fiber_physics_loss_db_per_m_accepts_positive_zero_and_negative() -> None:
    assert FiberPhysicsCfg(loss_db_per_m=0.2).loss_db_per_m == 0.2
    assert FiberPhysicsCfg(loss_db_per_m=0.0).loss_db_per_m == 0.0
    assert FiberPhysicsCfg(loss_db_per_m=-0.2).loss_db_per_m == -0.2


@pytest.mark.unit
def test_fiber_amp_wrap_accepts_gamma_only_nonlinearity_inputs() -> None:
    cfg = FiberAmpWrapCfg(
        power_out_w=2.0,
        physics=FiberPhysicsCfg(
            gamma_1_per_w_m=0.025,
            dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
        ),
        numerics=ToyPhaseNumericsCfg(),
    )

    assert cfg.physics.gamma_1_per_w_m == pytest.approx(0.025)


@pytest.mark.unit
def test_fiber_amp_wrap_accepts_n2_and_aeff_only_nonlinearity_inputs() -> None:
    cfg = FiberAmpWrapCfg(
        power_out_w=2.0,
        physics=FiberPhysicsCfg(
            n2_m2_per_w=2.6e-20,
            aeff_m2=40e-12,
            dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
        ),
        numerics=ToyPhaseNumericsCfg(),
    )

    assert cfg.physics.n2_m2_per_w == pytest.approx(2.6e-20)
    assert cfg.physics.aeff_m2 == pytest.approx(40e-12)


@pytest.mark.unit
def test_fiber_amp_wrap_rejects_gamma_plus_n2_aeff_nonlinearity_inputs() -> None:
    with pytest.raises(ValidationError, match="must provide exactly one nonlinearity input"):
        FiberAmpWrapCfg(
            power_out_w=2.0,
            physics=FiberPhysicsCfg(
                gamma_1_per_w_m=0.025,
                n2_m2_per_w=2.6e-20,
                aeff_m2=40e-12,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=ToyPhaseNumericsCfg(),
        )


@pytest.mark.unit
def test_fiber_amp_wrap_rejects_partial_n2_nonlinearity_inputs() -> None:
    with pytest.raises(ValidationError, match="requires both n2_m2_per_w and aeff_m2"):
        FiberAmpWrapCfg(
            power_out_w=2.0,
            physics=FiberPhysicsCfg(
                n2_m2_per_w=2.6e-20,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=ToyPhaseNumericsCfg(),
        )
