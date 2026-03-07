from __future__ import annotations


def test_tuning_package_imports() -> None:
    import cpa_sim.tuning as tuning

    assert tuning.TuningRunConfig.__name__ == "TuningRunConfig"
