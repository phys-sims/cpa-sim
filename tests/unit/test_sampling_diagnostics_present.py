from __future__ import annotations

import pytest

from cpa_sim.models import PipelineConfig
from cpa_sim.pipeline import run_pipeline


@pytest.mark.unit
def test_sampling_diagnostics_are_emitted_per_stage() -> None:
    result = run_pipeline(PipelineConfig())

    stage_prefix = "cpa.laser_init."
    expected_keys = {
        f"{stage_prefix}sampling.edge_energy_fraction_t",
        f"{stage_prefix}sampling.nyquist_energy_fraction_w",
        f"{stage_prefix}sampling.n_samples",
        f"{stage_prefix}sampling.dt_fs",
        f"{stage_prefix}sampling.time_window_fs",
    }

    assert expected_keys.issubset(result.metrics.keys())
