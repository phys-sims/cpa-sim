from __future__ import annotations

import pytest


@pytest.mark.unit
def test_tuning_package_imports() -> None:
    import cpa_sim.tuning as tuning

    assert tuning.TuningRunConfig.__name__ == "TuningRunConfig"
