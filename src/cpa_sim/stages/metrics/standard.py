from __future__ import annotations

import numpy as np

from cpa_sim.metrics import amplification_ratio, normalized_cross_correlation
from cpa_sim.models.config import MetricsCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.utils import maybe_emit_stage_plots


class StandardMetricsStage(LaserStage[MetricsCfg]):
    def __init__(self, cfg: MetricsCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        t = np.asarray(out.pulse.grid.t)
        intensity = out.pulse.intensity_t
        spec = out.pulse.spectrum_w

        energy = float(np.sum(intensity) * out.pulse.grid.dt)
        peak = float(np.max(intensity))
        fwhm = _interpolated_fwhm_fs(t=t, intensity=intensity, peak=peak)
        bandwidth = float(np.sqrt(np.average((np.asarray(out.pulse.grid.w) ** 2), weights=spec)))

        laser_energy = float(out.metrics.get("laser.energy_au", 0.0))
        amp_ratio = amplification_ratio(energy_out=energy, energy_in=laser_energy)

        reference = out.meta.get("reference", {})
        reference_intensity = np.asarray(reference.get("intensity_t", []), dtype=float)
        reference_spectrum = np.asarray(reference.get("spectrum_w", []), dtype=float)

        temporal_similarity = (
            normalized_cross_correlation(reference_intensity, intensity)
            if reference_intensity.shape == intensity.shape
            else 0.0
        )
        spectral_similarity = (
            normalized_cross_correlation(reference_spectrum, spec)
            if reference_spectrum.shape == spec.shape
            else 0.0
        )

        stage_metrics = {
            "summary.energy_au": energy,
            "summary.peak_intensity_au": peak,
            "summary.fwhm_fs": fwhm,
            "summary.bandwidth_rad_per_fs": bandwidth,
            "summary.amplification_ratio": amp_ratio,
            "summary.temporal_shape_similarity": temporal_similarity,
            "summary.spectral_shape_similarity": spectral_similarity,
        }
        out.metrics.update(stage_metrics)
        out.artifacts.update(maybe_emit_stage_plots(stage_name=self.name, state=out, policy=policy))
        return StageResult(state=out, metrics=stage_metrics)


def _interpolated_fwhm_fs(t: np.ndarray, intensity: np.ndarray, peak: float) -> float:
    if peak <= 0.0 or intensity.size < 2:
        return 0.0

    peak_idx = int(np.argmax(intensity))
    half = peak / 2.0

    left_cross_idx: int | None = None
    for idx in range(peak_idx, 0, -1):
        if intensity[idx - 1] < half <= intensity[idx]:
            left_cross_idx = idx
            break

    right_cross_idx: int | None = None
    for idx in range(peak_idx, intensity.size - 1):
        if intensity[idx] >= half > intensity[idx + 1]:
            right_cross_idx = idx
            break

    if left_cross_idx is None or right_cross_idx is None:
        return 0.0

    t_left = _interp_crossing(
        x0=float(t[left_cross_idx - 1]),
        x1=float(t[left_cross_idx]),
        y0=float(intensity[left_cross_idx - 1]),
        y1=float(intensity[left_cross_idx]),
        target=half,
    )
    t_right = _interp_crossing(
        x0=float(t[right_cross_idx]),
        x1=float(t[right_cross_idx + 1]),
        y0=float(intensity[right_cross_idx]),
        y1=float(intensity[right_cross_idx + 1]),
        target=half,
    )
    return float(t_right - t_left)


def _interp_crossing(*, x0: float, x1: float, y0: float, y1: float, target: float) -> float:
    if y1 == y0:
        return x0
    return x0 + (target - y0) * (x1 - x0) / (y1 - y0)
