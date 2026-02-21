"""Compatibility import surface for phys-pipeline primitives."""

from __future__ import annotations

try:
    from phys_pipeline.pipeline import SequentialPipeline
    from phys_pipeline.policy import PolicyBag, PolicyLike
    from phys_pipeline.types import PipelineStage, StageConfig, StageResult, State
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "cpa-sim requires runtime dependency 'phys-pipeline'. "
        "Install project runtime dependencies (for example: `pip install -e .`)."
    ) from exc

__all__ = [
    "PipelineStage",
    "PolicyBag",
    "PolicyLike",
    "SequentialPipeline",
    "StageConfig",
    "StageResult",
    "State",
]
