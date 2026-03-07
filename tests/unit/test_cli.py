from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cpa_sim import cli


@pytest.mark.unit
def test_parse_args_auto_window_defaults() -> None:
    args = cli._parse_args(
        [
            "run",
            "configs/examples/basic_cpa.yaml",
            "--out",
            "out/basic",
            "--auto-window",
        ]
    )
    assert args.auto_window is True
    assert args.auto_window_stages == "stretcher,compressor"
    assert args.auto_window_print is False


@pytest.mark.unit
def test_main_applies_auto_window_policy_from_cli_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    @dataclass(frozen=True)
    class _DummyRunOutput:
        result: Any
        policy: dict[str, Any]
        artifacts: dict[str, str]
        metrics_payload: dict[str, Any]
        artifacts_payload: dict[str, Any]

    def _fake_run_pipeline_with_plot_policy(
        cfg: Any, *, stage_plot_dir: Path, policy_overrides: dict[str, Any] | None = None
    ) -> _DummyRunOutput:
        captured["policy_overrides"] = dict(policy_overrides or {})
        state = SimpleNamespace(meta={}, metrics={}, artifacts={}, pulse=SimpleNamespace())
        result = SimpleNamespace(state=state, metrics={}, artifacts={})
        return _DummyRunOutput(
            result=result,
            policy={},
            artifacts={},
            metrics_payload={},
            artifacts_payload={},
        )

    monkeypatch.setattr(cli, "_load_config", lambda path: object())
    monkeypatch.setattr(cli, "run_pipeline_with_plot_policy", _fake_run_pipeline_with_plot_policy)
    monkeypatch.setattr(cli, "write_json", lambda path, payload: None)
    monkeypatch.setattr(
        cli,
        "build_validation_report",
        lambda cfg, result, artifacts: SimpleNamespace(model_dump=lambda mode: {}),
    )
    monkeypatch.setattr(cli, "render_markdown_report", lambda report: "ok")

    out_dir = tmp_path / "out"
    rc = cli.main(
        [
            "run",
            "configs/examples/basic_cpa.yaml",
            "--out",
            str(out_dir),
            "--auto-window",
            "--auto-window-stages",
            "stretcher, compressor",
            "--auto-window-print",
        ]
    )

    assert rc == 0
    assert captured["policy_overrides"] == {
        "cpa.auto_window.enabled": True,
        "cpa.auto_window.stages": ["stretcher", "compressor"],
        "cpa.auto_window.print": True,
    }
