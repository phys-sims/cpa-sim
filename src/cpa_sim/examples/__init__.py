"""Runnable and reusable example helpers for cpa-sim."""

from cpa_sim.examples.end_to_end_1560nm import run_example as run_end_to_end_1560nm_example
from cpa_sim.examples.fiber_amp_spm import run_example as run_fiber_amp_spm_example
from cpa_sim.examples.simple_fiber_dispersion import (
    run_example as run_simple_fiber_dispersion_example,
)
from cpa_sim.examples.treacy_stage_validation import (
    run_example as run_treacy_stage_validation_example,
)
from cpa_sim.examples.wave_breaking_raman import run_example as run_wave_breaking_raman_example

__all__ = [
    "run_end_to_end_1560nm_example",
    "run_fiber_amp_spm_example",
    "run_simple_fiber_dispersion_example",
    "run_treacy_stage_validation_example",
    "run_wave_breaking_raman_example",
]
