from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cpa_sim.models.config import MetricsCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.metrics.standard import StandardMetricsStage


def _build_state_with_resample_reference() -> LaserState:
    t = np.linspace(-100.0, 100.0, 64)
    dt = float(t[1] - t[0])
    envelope = np.exp(-((t / 25.0) ** 2))
    intensity = np.abs(envelope) ** 2
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(envelope))) ** 2
    w = np.linspace(-1.0, 1.0, t.size)
    dw = float(w[1] - w[0])

    t_ref = np.linspace(-100.0, 100.0, 48)
    w_ref = np.linspace(-1.0, 1.0, 48)
    intensity_ref = np.exp(-((t_ref / 30.0) ** 2))
    spectrum_ref = np.exp(-((w_ref / 0.25) ** 2))

    pulse = PulseState(
        grid=PulseGrid(t=t.tolist(), w=w.tolist(), dt=dt, dw=dw, center_wavelength_nm=1030.0),
        field_t=envelope.astype(complex),
        field_w=np.fft.fftshift(np.fft.fft(envelope)).astype(complex),
        intensity_t=intensity,
        spectrum_w=spectrum,
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={
            "reference": {
                "t_fs": t_ref.tolist(),
                "w_rad_per_fs": w_ref.tolist(),
                "intensity_t": intensity_ref.tolist(),
                "spectrum_w": spectrum_ref.tolist(),
            }
        },
        metrics={},
    )


@pytest.mark.unit
def test_metrics_stage_emits_input_output_overlay_plots(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")

    result = StandardMetricsStage(MetricsCfg()).process(
        _build_state_with_resample_reference(),
        policy={
            "cpa.emit_stage_plots": True,
            "cpa.stage_plot_dir": str(tmp_path),
        },
    )

    for key in ("metrics.plot_time_intensity_overlay", "metrics.plot_spectrum_overlay"):
        assert key in result.state.artifacts
        path = Path(result.state.artifacts[key])
        assert path.exists()
        assert path.stat().st_size > 0
        assert "<svg" in path.read_text(encoding="utf-8")
