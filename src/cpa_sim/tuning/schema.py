from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TunableParameter(BaseModel):
    """Single bounded parameter applied to a pipeline config dot path."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    bounds: tuple[float, float]
    transform: Literal["identity", "log10", "ln"] | None = None

    @field_validator("name", "path")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("parameter names and paths must be non-empty strings")
        return value

    @field_validator("bounds")
    @classmethod
    def _validate_bounds(cls, value: tuple[float, float]) -> tuple[float, float]:
        lower, upper = value
        if lower >= upper:
            raise ValueError("parameter bounds must satisfy lower < upper")
        return value


class OptimizerConfig(BaseModel):
    """Generic optimizer settings backed by phys-sims-utils strategies."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["cmaes"] = "cmaes"
    max_evals: int = 20
    sigma0: float = 0.25
    population_size: int | None = None

    @field_validator("max_evals")
    @classmethod
    def _validate_max_evals(cls, value: int) -> int:
        if value < 1:
            raise ValueError("optimizer.max_evals must be >= 1")
        return value

    @field_validator("sigma0")
    @classmethod
    def _validate_sigma0(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("optimizer.sigma0 must be > 0")
        return value


class ExecutionConfig(BaseModel):
    """Deterministic execution controls for each objective evaluation."""

    model_config = ConfigDict(frozen=True)

    seed: int = 0
    emit_stage_plots: bool = False
    policy_overrides: dict[str, Any] = Field(default_factory=dict)


class OutputConfig(BaseModel):
    """Output paths and optional best-point rerun controls."""

    model_config = ConfigDict(frozen=True)

    out_dir: Path = Field(default=Path("out/tuning/optimize"))
    best_config_name: str = "best_config.yaml"
    rerun_best_with_plots: bool = False
    best_run_dirname: str = "best_run"


class TuningObjective(BaseModel):
    """Objective definition based on an output metric key."""

    model_config = ConfigDict(frozen=True)

    metric: str
    direction: Literal["minimize", "maximize"] = "minimize"


class TuneConfig(BaseModel):
    """Top-level schema for the generic tuning engine."""

    model_config = ConfigDict(frozen=True)

    base_pipeline_config: Path | dict[str, Any]
    parameters: list[TunableParameter]
    objective: TuningObjective
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @model_validator(mode="after")
    def _validate_unique_paths(self) -> TuneConfig:
        seen: set[str] = set()
        for parameter in self.parameters:
            if parameter.path in seen:
                raise ValueError(f"Duplicate parameter path '{parameter.path}'.")
            seen.add(parameter.path)
        return self


# Back-compat wrappers used by older tests/imports.
class TuningParameter(TunableParameter):
    pass


class TuningRunConfig(TuneConfig):
    pass
