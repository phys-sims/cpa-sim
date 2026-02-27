from __future__ import annotations

from typing import cast

import numpy as np

from cpa_sim.models.config import LaserGenCfg
from cpa_sim.models.state import BeamState, LaserState, PulseGrid, PulseState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.physics import rep_rate_hz, resolve_intensity_fwhm_fs, resolve_peak_power_w
from cpa_sim.physics.pulse_resolve import PulseSpecLike
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
        pulse_spec = cast(PulseSpecLike, spec.pulse)
        width_fs_eff = resolve_intensity_fwhm_fs(pulse_spec)
        peak_power_w = resolve_peak_power_w(pulse_spec, width_fs=width_fs_eff)
        i0 = peak_power_w
        if spec.pulse.shape == "gaussian":
            intensity = i0 * np.exp(-4.0 * np.log(2.0) * (t / width_fs_eff) ** 2)
        else:
            sech_fwhm_factor = 2.0 * np.arccosh(np.sqrt(2.0))
            t0 = width_fs_eff / sech_fwhm_factor
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
        out.meta["laser.intensity_fwhm_fs"] = float(width_fs_eff)
        out.meta["laser.peak_power_w"] = float(peak_power_w)
        if spec.pulse.intensity_autocorr_fwhm_fs is not None:
            out.meta["laser.intensity_autocorr_fwhm_fs_input"] = float(
                spec.pulse.intensity_autocorr_fwhm_fs
            )
        pulse_energy_j = float(np.sum(intensity) * dt * 1e-15)
        out.meta["laser.pulse_energy_j"] = pulse_energy_j
        rep_rate = float(spec.pulse.rep_rate_mhz)
        if rep_rate > 0.0:
            out.meta["laser.avg_power_w"] = pulse_energy_j * rep_rate_hz(rep_rate)
        stage_metrics = {
            "laser.energy_au": float(np.sum(intensity) * dt),
            "laser.peak_intensity_au": float(np.max(intensity)),
            "laser.intensity_fwhm_fs": float(width_fs_eff),
            "laser.peak_power_w": float(peak_power_w),
            "laser.pulse_energy_j": pulse_energy_j,
        }
        if rep_rate > 0.0:
            stage_metrics["laser.avg_power_w"] = out.meta["laser.avg_power_w"]
        out.metrics.update(stage_metrics)
        out.artifacts.update(maybe_emit_stage_plots(stage_name=self.name, state=out, policy=policy))
        return StageResult(state=out, metrics=stage_metrics)
