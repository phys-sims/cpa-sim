from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TuningParameter(BaseModel):
    """Single bounded tuning variable addressed by a dot path in pipeline config."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    lower: float
    upper: float
    transform: str | None = None


class TuningObjective(BaseModel):
    """Objective specification scaffold for future task-specific tuners."""

    model_config = ConfigDict(frozen=True)

    name: str = "placeholder"
    direction: str = "minimize"


class TuningRunConfig(BaseModel):
    """Top-level tuning scaffold config."""

    model_config = ConfigDict(frozen=True)

    base_pipeline_config: Path
    out_dir: Path = Field(default=Path("out/tuning/optimize"))
    max_evals: int = 20
    parameters: list[TuningParameter] = Field(default_factory=list)
    objective: TuningObjective = Field(default_factory=TuningObjective)
