from __future__ import annotations

import json

import pytest

from cpa_sim.reporting.validation_models import (
    ReportProvenance,
    StageReport,
    ValidationReport,
    ValidationTierReference,
)


@pytest.mark.unit
def test_validation_report_schema_serialization_roundtrip() -> None:
    report = ValidationReport(
        provenance=ReportProvenance(
            run_id="run-123",
            seed=7,
            config_hash="abc123",
            version="0.1.0",
            git_sha="deadbeef",
        ),
        validation_tiers=[
            ValidationTierReference(
                tier="unit",
                marker="unit",
                references=["tests/unit", "docs/adr/ADR-0003-validation-tiers-ci-policy.md"],
            )
        ],
        summary_metrics={"cpa.metrics.summary.energy_au": 1.0},
        stages=[
            StageReport(
                stage="metrics",
                metrics={"energy_au": 1.0},
                artifacts={"plot_time_intensity": "out/stage_plots/metrics_time_intensity.svg"},
            )
        ],
    )

    payload = report.model_dump(mode="json")
    as_json = json.dumps(payload)
    parsed = ValidationReport.model_validate_json(as_json)

    assert parsed.schema_version == "cpa.validation_report.v1"
    assert parsed.provenance.seed == 7
    assert parsed.stages[0].stage == "metrics"
    assert parsed.stages[0].artifacts["plot_time_intensity"].endswith(".svg")
