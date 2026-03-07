"""Runnable and reusable example helpers for cpa-sim."""

from cpa_sim.examples.canonical_1560nm_chain import (
    run_example as run_canonical_1560nm_chain_example,
)
from cpa_sim.examples.gnlse_dispersive_wave import run_example as run_gnlse_dispersive_wave_example
from cpa_sim.examples.spm_after_fiber_amp import run_example as run_spm_after_fiber_amp_example
from cpa_sim.examples.treacy_compressor_probe import run_probe as run_treacy_compressor_probe
from cpa_sim.examples.treacy_stage_validation import (
    main as run_treacy_stage_validation_artifacts,
)
from cpa_sim.examples.wust_gnlse_fiber_example import run_example as run_wust_gnlse_fiber_example

__all__ = [
    "run_canonical_1560nm_chain_example",
    "run_gnlse_dispersive_wave_example",
    "run_treacy_compressor_probe",
    "run_treacy_stage_validation_artifacts",
    "run_wust_gnlse_fiber_example",
    "run_spm_after_fiber_amp_example",
]
