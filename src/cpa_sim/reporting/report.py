from __future__ import annotations

import importlib.metadata
import subprocess
from pathlib import Path

from cpa_sim.models import PipelineConfig
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.reporting.validation_models import (
    ReportProvenance,
    StageReport,
    ValidationReport,
    ValidationTierReference,
)


def build_validation_report(
    *, cfg: PipelineConfig, result: StageResult, artifacts: dict[str, str]
) -> ValidationReport:
    provenance_meta = result.state.meta.get("provenance", {})
    provenance = ReportProvenance(
        run_id=str(provenance_meta.get("run_id", result.state.meta.get("run_id", "unknown"))),
        seed=int(result.state.meta.get("seed", cfg.runtime.seed)),
        config_hash=str(result.state.meta.get("config_hash", "unknown")),
        created_utc=_maybe_str(provenance_meta.get("created_utc")),
        policy_hash=_maybe_str(provenance_meta.get("policy_hash")),
        version=_get_package_version(),
        git_sha=_get_git_sha(),
    )

    return ValidationReport(
        provenance=provenance,
        validation_tiers=_default_tier_references(),
        summary_metrics=result.metrics,
        stages=_build_stage_reports(metrics=result.metrics, artifacts=artifacts),
    )


def render_markdown_report(report: ValidationReport) -> str:
    lines = [
        "# CPA Simulation Validation Report",
        "",
        f"- Run ID: `{report.provenance.run_id}`",
        f"- Seed: `{report.provenance.seed}`",
        f"- Config hash: `{report.provenance.config_hash}`",
        f"- Version: `{report.provenance.version or 'unknown'}`",
        f"- Git SHA: `{report.provenance.git_sha or 'unknown'}`",
        "",
        "## Summary metrics",
    ]
    for key, value in sorted(report.summary_metrics.items()):
        lines.append(f"- `{key}`: `{value:.6g}`")

    lines.extend(["", "## Validation tiers"])
    for tier in report.validation_tiers:
        refs = ", ".join(tier.references)
        lines.append(f"- `{tier.tier}` (`{tier.marker}`): {refs}")

    lines.extend(["", "## Stage outputs"])
    for stage in report.stages:
        lines.append(f"### `{stage.stage}`")
        if stage.metrics:
            lines.append("- Metrics:")
            for key, value in sorted(stage.metrics.items()):
                lines.append(f"  - `{key}`: `{value:.6g}`")
        if stage.artifacts:
            lines.append("- Artifacts:")
            for artifact_key, artifact_path in sorted(stage.artifacts.items()):
                lines.append(f"  - `{artifact_key}`: `{artifact_path}`")

    return "\n".join(lines) + "\n"


def _build_stage_reports(
    *, metrics: dict[str, float], artifacts: dict[str, str]
) -> list[StageReport]:
    stage_names = set(_group_metric_keys(metrics)) | set(_group_artifacts(artifacts))
    grouped_metrics = _group_metric_keys(metrics)
    grouped_artifacts = _group_artifacts(artifacts)

    reports: list[StageReport] = []
    for stage_name in sorted(stage_names):
        reports.append(
            StageReport(
                stage=stage_name,
                metrics=grouped_metrics.get(stage_name, {}),
                artifacts=grouped_artifacts.get(stage_name, {}),
            )
        )
    return reports


def _group_metric_keys(metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for key, value in metrics.items():
        parts = key.split(".", 3)
        if len(parts) >= 4 and parts[0] == "cpa":
            stage = parts[1]
            metric_name = parts[3]
        else:
            stage = "overall"
            metric_name = key
        grouped.setdefault(stage, {})[metric_name] = value
    return grouped


def _group_artifacts(artifacts: dict[str, str]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = {}
    for key, value in artifacts.items():
        if "." in key:
            stage, artifact_name = key.split(".", 1)
        else:
            stage, artifact_name = "run", key
        grouped.setdefault(stage, {})[artifact_name] = value
    return grouped


def _default_tier_references() -> list[ValidationTierReference]:
    return [
        ValidationTierReference(
            tier="unit",
            marker="unit",
            references=["tests/unit", "docs/adr/ADR-0003-validation-tiers-ci-policy.md"],
        ),
        ValidationTierReference(
            tier="integration",
            marker="integration",
            references=["tests/integration", "docs/adr/ADR-0003-validation-tiers-ci-policy.md"],
        ),
        ValidationTierReference(
            tier="physics",
            marker="physics",
            references=["tests/physics", "docs/adr/ADR-0003-validation-tiers-ci-policy.md"],
        ),
    ]


def _get_package_version() -> str | None:
    try:
        return importlib.metadata.version("cpa-sim")
    except importlib.metadata.PackageNotFoundError:
        return None


def _get_git_sha() -> str | None:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return output.strip() or None


def _maybe_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
