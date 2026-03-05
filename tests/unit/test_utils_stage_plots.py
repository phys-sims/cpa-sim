from __future__ import annotations

from pathlib import Path

import numpy as np

from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.utils import maybe_emit_stage_plots


def _build_state() -> LaserState:
    grid = PulseGrid(
        t=np.linspace(-10.0, 10.0, 8),
        w=np.linspace(-3.0, 3.0, 8),
        dt=2.5,
        dw=0.75,
        center_wavelength_nm=1560.0,
    )
    field_t = np.ones(8, dtype=np.complex128)
    field_w = np.ones(8, dtype=np.complex128)
    intensity_t = np.abs(field_t) ** 2
    spectrum_w = np.abs(field_w) ** 2
    pulse = PulseState(
        grid=grid,
        field_t=field_t,
        field_w=field_w,
        intensity_t=intensity_t,
        spectrum_w=spectrum_w,
    )
    return LaserState(
        pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={}, artifacts={}
    )


def test_stage_spectrum_plot_uses_tighter_autoscale_threshold(
    monkeypatch: object, tmp_path: Path
) -> None:
    state = _build_state()
    calls: list[dict[str, object]] = []

    def _fake_plot_line_series(**kwargs: object) -> Path:
        calls.append(kwargs)
        out_path = Path(str(kwargs["out_path"]))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("stub", encoding="utf-8")
        return out_path

    monkeypatch.setattr("cpa_sim.utils.plot_line_series", _fake_plot_line_series)

    artifacts = maybe_emit_stage_plots(
        stage_name="treacy_compressor",
        state=state,
        policy={"cpa.emit_stage_plots": True, "cpa.stage_plot_dir": str(tmp_path)},
    )

    assert f"treacy_compressor.plot_time_intensity" in artifacts
    assert f"treacy_compressor.plot_spectrum" in artifacts
    assert len(calls) == 2
    assert "auto_xlim_threshold_fraction" not in calls[0]
    assert calls[1]["auto_xlim_threshold_fraction"] == 1e-2
