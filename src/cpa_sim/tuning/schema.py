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


class SoftConstraint(BaseModel):
    """Soft objective constraint converted into a differentiable penalty term."""

    model_config = ConfigDict(frozen=True)

    metric: str
    lower: float | None = None
    upper: float | None = None
    target: float | None = None
    weight: float = 1.0
    power: float = 2.0

    @field_validator("metric")
    @classmethod
    def _validate_metric_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("constraint.metric must be a non-empty dotted metric path")
        return value

    @field_validator("weight", "power")
    @classmethod
    def _validate_positive_scalars(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("constraint weight and power must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_constraint_shape(self) -> SoftConstraint:
        if self.lower is None and self.upper is None and self.target is None:
            raise ValueError("constraint requires at least one of lower, upper, or target")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("constraint lower must be <= upper")
        return self


class TuningObjective(BaseModel):
    """Objective definition for scalar metric and spectrum/trace target fitting."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["metric", "spectral_rmse", "spectral_correlation"] = "metric"

    # Legacy scalar metric objective fields.
    metric: str | None = None
    direction: Literal["minimize", "maximize"] = "minimize"

    # Scalar-target metric objective fields.
    metric_path: str | None = None
    target_value: float | None = None

    # Spectral/time-trace target objective fields.
    target_csv: Path | None = None
    target_x_column: str | int | None = None
    target_y_column: str | int | None = None
    target_trace: Literal["spectrum", "time_trace"] = "spectrum"
    target_axis: Literal["omega_offset_rad_per_fs", "wavelength_nm", "time_fs"] | None = None
    normalization: Literal["none", "peak", "area"] = "peak"
    roi: tuple[float, float] | None = None

    # Composite weighting and penalties.
    weight: float = 1.0
    constraints: list[SoftConstraint] = Field(default_factory=list)
    exception_penalty: float = 1e12

    @field_validator("metric", "metric_path")
    @classmethod
    def _validate_optional_metric_paths(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("objective metric paths must be non-empty")
        return value

    @field_validator("target_x_column", "target_y_column")
    @classmethod
    def _validate_optional_column_names(
        cls,
        value: str | int | None,
    ) -> str | int | None:
        if isinstance(value, str) and not value.strip():
            raise ValueError("target column names must be non-empty when provided")
        if isinstance(value, int) and value < 0:
            raise ValueError("target column indices must be >= 0")
        return value

    @field_validator("weight", "exception_penalty")
    @classmethod
    def _validate_positive_weights(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("objective weight and exception_penalty must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_shape(self) -> TuningObjective:
        if self.roi is not None:
            low, high = self.roi
            if low >= high:
                raise ValueError("objective.roi must satisfy low < high")

        resolved_metric_path = self.metric_path or self.metric
        if self.kind == "metric":
            if resolved_metric_path is None:
                raise ValueError("metric objective requires 'metric' or 'metric_path'")
            object.__setattr__(self, "metric_path", resolved_metric_path)
            return self

        if self.target_csv is None:
            raise ValueError(f"{self.kind} objective requires target_csv")

        if self.target_trace == "time_trace":
            if self.target_axis not in {None, "time_fs"}:
                raise ValueError("time_trace objectives require target_axis='time_fs'")
            object.__setattr__(self, "target_axis", "time_fs")
        elif self.target_axis == "time_fs":
            raise ValueError("spectrum objectives cannot use target_axis='time_fs'")
        elif self.target_axis is None:
            object.__setattr__(self, "target_axis", "omega_offset_rad_per_fs")

        return self

    @property
    def target_csv_path(self) -> Path:
        if self.target_csv is None:
            raise ValueError("target_csv is required for non-metric objectives")
        return self.target_csv


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
