"""Compatibility re-exports for legacy imports.

This module intentionally forwards to the stable models in ``cpa_sim.models.state``.
"""

from cpa_sim.models.state import LaserSpec, LaserState

__all__ = ["LaserSpec", "LaserState"]
