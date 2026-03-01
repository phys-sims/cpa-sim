"""Runnable and reusable example helpers for cpa-sim."""

from cpa_sim.examples.canonical_1560nm_chain import (
    run_example as run_canonical_1560nm_chain_example,
)
from cpa_sim.examples.gnlse_dispersive_wave_showcase import (
    run_showcase as run_gnlse_dispersive_wave_showcase,
)
from cpa_sim.examples.treacy_compressor_probe import run_probe as run_treacy_compressor_probe
from cpa_sim.examples.wust_gnlse_fiber_example import run_example as run_wust_gnlse_fiber_example

__all__ = [
    "run_canonical_1560nm_chain_example",
    "run_gnlse_dispersive_wave_showcase",
    "run_treacy_compressor_probe",
    "run_wust_gnlse_fiber_example",
]
