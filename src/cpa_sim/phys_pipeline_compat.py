"""Compatibility import surface for phys-pipeline primitives."""

from __future__ import annotations

import site
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, cast


def _load_submodule_without_package_init(mod_name: str, file_path: Path) -> Any:
    spec = spec_from_file_location(mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot build import spec for {mod_name} from {file_path}")
    module = module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


try:
    from phys_pipeline.pipeline import SequentialPipeline
    from phys_pipeline.policy import PolicyBag, PolicyLike
    from phys_pipeline.types import PipelineStage, StageConfig, StageResult, State
except Exception:  # pragma: no cover
    pkg_dir: Path | None = None
    for site_dir in site.getsitepackages():
        candidate = Path(site_dir) / "phys_pipeline"
        if candidate.exists():
            pkg_dir = candidate
            break
    if pkg_dir is None:
        raise ImportError("phys-pipeline is required but not installed.")

    package_module = types.ModuleType("phys_pipeline")
    package_module.__path__ = [str(pkg_dir)]
    sys.modules.setdefault("phys_pipeline", package_module)

    _load_submodule_without_package_init("phys_pipeline.policy", pkg_dir / "policy.py")
    _load_submodule_without_package_init("phys_pipeline.types", pkg_dir / "types.py")
    _load_submodule_without_package_init("phys_pipeline.hashing", pkg_dir / "hashing.py")
    _load_submodule_without_package_init("phys_pipeline.record", pkg_dir / "record.py")
    _load_submodule_without_package_init("phys_pipeline.accumulator", pkg_dir / "accumulator.py")
    pipeline_module = _load_submodule_without_package_init(
        "phys_pipeline.pipeline", pkg_dir / "pipeline.py"
    )

    policy_module = sys.modules["phys_pipeline.policy"]
    types_module = sys.modules["phys_pipeline.types"]

    PolicyBag = cast(Any, policy_module.PolicyBag)  # type: ignore[misc]
    PolicyLike = cast(Any, policy_module.PolicyLike)
    PipelineStage = cast(Any, types_module.PipelineStage)  # type: ignore[misc]
    StageConfig = cast(Any, types_module.StageConfig)  # type: ignore[misc]
    StageResult = cast(Any, types_module.StageResult)  # type: ignore[misc]
    State = cast(Any, types_module.State)  # type: ignore[misc]
    SequentialPipeline = cast(Any, pipeline_module.SequentialPipeline)  # type: ignore[misc]

__all__ = [
    "PipelineStage",
    "PolicyBag",
    "PolicyLike",
    "SequentialPipeline",
    "StageConfig",
    "StageResult",
    "State",
]
