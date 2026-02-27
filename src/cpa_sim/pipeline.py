from __future__ import annotations

import hashlib
import json
from typing import Any, cast

import numpy as np

from cpa_sim.models import PipelineConfig, RunProvenance
from cpa_sim.models.config import FiberAmpWrapCfg, FiberCfg, PipelineStageCfg, SimpleGainCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.phys_pipeline_compat import (
    PipelineStage,
    PolicyLike,
    SequentialPipeline,
    StageResult,
)
from cpa_sim.stages.registry import (
    build_amp_stage,
    build_fiber_stage,
    build_free_space_stage,
    build_laser_gen_stage,
    build_metrics_stage,
)


def _build_configurable_stages(cfg: PipelineConfig) -> list[PipelineStage[LaserState, Any]]:
    if cfg.stages is None:
        ordered: list[PipelineStageCfg] = [cfg.stretcher, cfg.fiber, cfg.amp, cfg.compressor]
    else:
        ordered = cfg.stages

    stages: list[PipelineStage[LaserState, Any]] = []
    for stage_cfg in ordered:
        if isinstance(stage_cfg, FiberAmpWrapCfg):
            stages.append(build_amp_stage(stage_cfg))
        elif isinstance(stage_cfg, FiberCfg):
            stages.append(build_fiber_stage(stage_cfg))
        elif isinstance(stage_cfg, SimpleGainCfg):
            stages.append(build_amp_stage(stage_cfg))
        else:
            stages.append(build_free_space_stage(stage_cfg))
    return stages


def build_pipeline(
    cfg: PipelineConfig, *, policy: PolicyLike | None = None
) -> SequentialPipeline[LaserState]:
    """Build a deterministic sequential CPA chain aligned with phys-pipeline contracts."""
    stages: list[PipelineStage[LaserState, Any]] = [
        build_laser_gen_stage(cfg.laser_gen),
        *_build_configurable_stages(cfg),
        build_metrics_stage(cfg.metrics),
    ]
    return cast(
        SequentialPipeline[LaserState],
        SequentialPipeline(stages=stages, name="cpa", policy=policy),
    )


def run_pipeline(
    cfg: PipelineConfig, *, policy: PolicyLike | None = None
) -> StageResult[LaserState]:
    pipeline = build_pipeline(cfg, policy=policy)
    config_hash = hashlib.sha256(
        json.dumps(cfg.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    policy_hash = _hash_policy(policy)
    initial_state = _empty_state(
        seed=cfg.runtime.seed, config_hash=config_hash, policy_hash=policy_hash
    )
    result = pipeline.run(initial_state, policy=policy)
    result.state.meta.setdefault("config_hash", config_hash)
    result.state.meta.setdefault("seed", cfg.runtime.seed)
    result.state.meta.setdefault(
        "run_id", result.state.meta.get("provenance", {}).get("run_id", "unknown")
    )
    return result


def _hash_policy(policy: PolicyLike | None) -> str | None:
    if policy is None:
        return None
    return hashlib.sha256(
        json.dumps(policy, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _empty_state(*, seed: int, config_hash: str, policy_hash: str | None) -> LaserState:
    provenance = RunProvenance.from_seed_and_hash(
        seed=seed, config_hash=config_hash, policy_hash=policy_hash
    )
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={"provenance": provenance.model_dump(mode="json")},
        metrics={},
        artifacts={},
    )
