"""Runnable and reusable example helpers for cpa-sim."""

from cpa_sim.examples.canonical_1560nm_chain import (
    run_example as run_canonical_1560nm_chain_example,
)
from cpa_sim.examples.toy_amp_case_ab_compare import (
    run_comparison as run_toy_amp_case_ab_comparison,
)
from cpa_sim.examples.treacy_compressor_probe import run_probe as run_treacy_compressor_probe
from cpa_sim.examples.wust_gnlse_fiber_example import run_example as run_wust_gnlse_fiber_example

__all__ = [
    "run_canonical_1560nm_chain_example",
    "run_toy_amp_case_ab_comparison",
    "run_treacy_compressor_probe",
    "run_wust_gnlse_fiber_example",
]
