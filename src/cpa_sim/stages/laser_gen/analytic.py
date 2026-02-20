from __future__ import annotations

import numpy as np

from cpa_sim.models.config import LaserGenCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.utils import maybe_emit_stage_plots


class AnalyticLaserGenStage(LaserStage[LaserGenCfg]):
    def __init__(self, cfg: LaserGenCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        spec = self.cfg.spec
        t = np.linspace(
            -0.5 * spec.pulse.time_window_fs,
            0.5 * spec.pulse.time_window_fs,
            spec.pulse.n_samples,
        )
        dt = float(t[1] - t[0])
        i0 = spec.pulse.amplitude**2
        if spec.pulse.shape == "gaussian":
            intensity = i0 * np.exp(-4.0 * np.log(2.0) * (t / spec.pulse.width_fs) ** 2)
        else:
            sech_fwhm_factor = 2.0 * np.arccosh(np.sqrt(2.0))
            t0 = spec.pulse.width_fs / sech_fwhm_factor
            intensity = i0 / np.cosh(t / t0) ** 2
        field_t = np.sqrt(intensity).astype(np.complex128)
        field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
        w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(t.size, d=dt))
        dw = float(w[1] - w[0])
        intensity = np.abs(field_t) ** 2
        spectrum = np.abs(field_w) ** 2

        out = state.deepcopy()
        out.pulse = PulseState(
            grid=PulseGrid(
                t=t.tolist(),
                w=w.tolist(),
                dt=dt,
                dw=dw,
                center_wavelength_nm=spec.pulse.center_wavelength_nm,
            ),
            field_t=field_t,
            field_w=field_w,
            intensity_t=intensity,
            spectrum_w=spectrum,
        )
        out.beam = BeamState(radius_mm=spec.beam.radius_mm, m2=spec.beam.m2)
        out.meta.setdefault("reference", {})
        out.meta["reference"].update(
            {
                "intensity_t": intensity.tolist(),
                "spectrum_w": spectrum.tolist(),
            }
        )
        out.meta["rep_rate_mhz"] = float(spec.pulse.rep_rate_mhz)
        stage_metrics = {
            "laser.energy_au": float(np.sum(intensity) * dt),
            "laser.peak_intensity_au": float(np.max(intensity)),
        }
        out.metrics.update(stage_metrics)
        out.artifacts.update(maybe_emit_stage_plots(stage_name=self.name, state=out, policy=policy))
        return StageResult(state=out, metrics=stage_metrics)
