from cpa_sim.models import FiberPhysicsCfg


def test_fiber_physics_loss_db_per_m_accepts_positive_zero_and_negative() -> None:
    assert FiberPhysicsCfg(loss_db_per_m=0.2).loss_db_per_m == 0.2
    assert FiberPhysicsCfg(loss_db_per_m=0.0).loss_db_per_m == 0.0
    assert FiberPhysicsCfg(loss_db_per_m=-0.2).loss_db_per_m == -0.2
