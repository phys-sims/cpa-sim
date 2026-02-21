from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReportProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    seed: int
    config_hash: str
    created_utc: str | None = None
    policy_hash: str | None = None
    version: str | None = None
    git_sha: str | None = None


class ValidationTierReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    tier: str
    marker: str
    references: list[str] = Field(default_factory=list)


class StageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: str
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "cpa.validation_report.v1"
    provenance: ReportProvenance
    validation_tiers: list[ValidationTierReference]
    summary_metrics: dict[str, float]
    stages: list[StageReport]
