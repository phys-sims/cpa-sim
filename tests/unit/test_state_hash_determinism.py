import numpy as np

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


def test_run_is_deterministic_for_same_config_and_seed() -> None:
    cfg = PipelineConfig()
    result_a = run_pipeline(cfg)
    result_b = run_pipeline(cfg)

    assert result_a.state.hashable_repr() == result_b.state.hashable_repr()
    assert result_a.metrics == result_b.metrics


def test_free_space_phase_preserves_energy() -> None:
    cfg = PipelineConfig()
    base = run_pipeline(cfg)
    energy_after = base.metrics["cpa.stretcher.stretcher.energy_au"]
    laser_energy = base.metrics["cpa.laser_init.laser.energy_au"]

    assert np.isclose(energy_after, laser_energy)


def test_policy_hash_is_recorded_in_provenance() -> None:
    cfg = PipelineConfig()
    result = run_pipeline(cfg, policy={"debug": {"enabled": True}})

    provenance = result.state.meta["provenance"]
    assert provenance["policy_hash"] is not None
