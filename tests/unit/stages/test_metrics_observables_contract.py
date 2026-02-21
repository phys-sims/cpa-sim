from __future__ import annotations

import numpy as np

from cpa_sim.models.config import MetricsCfg
from cpa_sim.models.observables import ObservableContract
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.stages.metrics.standard import StandardMetricsStage


def _build_state() -> LaserState:
    t = np.linspace(-100.0, 100.0, 64)
    dt = float(t[1] - t[0])
    envelope = np.exp(-((t / 25.0) ** 2))
    intensity = np.abs(envelope) ** 2
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(envelope))) ** 2
    w = np.linspace(-1.0, 1.0, t.size)
    dw = float(w[1] - w[0])

    pulse = PulseState(
        grid=PulseGrid(t=t.tolist(), w=w.tolist(), dt=dt, dw=dw, center_wavelength_nm=1030.0),
        field_t=envelope.astype(complex),
        field_w=np.fft.fftshift(np.fft.fft(envelope)).astype(complex),
        intensity_t=intensity,
        spectrum_w=spectrum,
    )
    return LaserState(pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={})


def test_standard_metrics_emits_observable_contract() -> None:
    result = StandardMetricsStage(MetricsCfg()).process(_build_state())

    assert "summary.ac_fwhm_fs" in result.metrics
    observables_payload = result.state.meta["observable_contract"]
    contract = ObservableContract.model_validate(observables_payload)
    names = {measurement.name for measurement in contract.measurements}
    assert names == {"intensity_fwhm", "intensity_autocorrelation_fwhm", "spectral_rms_width"}
