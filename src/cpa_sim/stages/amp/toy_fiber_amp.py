from __future__ import annotations

import numpy as np

from cpa_sim.models.config import ToyFiberAmpCfg
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.stages.base import LaserStage
from cpa_sim.utils import maybe_emit_stage_plots

_LOG10_DIV_10 = np.log(10.0) / 10.0
_DB_TO_NEPER_POWER = np.log(10.0) / 10.0


class ToyFiberAmpStage(LaserStage[ToyFiberAmpCfg]):
    """Toy split-step fiber amplifier: distributed gain/loss, beta2 dispersion, Kerr SPM only."""

    def __init__(self, cfg: ToyFiberAmpCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        out = state.deepcopy()
        field_t = np.asarray(out.pulse.field_t, dtype=np.complex128)
        w = np.asarray(out.pulse.grid.w, dtype=np.float64)

        energy_in = _energy_au(field_t, dt=out.pulse.grid.dt)
        peak_in = float(np.max(np.abs(field_t) ** 2))
        bandwidth_in = _rms_bandwidth_rad_per_fs(
            w=w, spectrum=np.abs(np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))) ** 2
        )

        dz = self.cfg.length_m / float(self.cfg.n_steps)
        g_power_per_m = _power_gain_coeff_per_m(self.cfg.gain_db, self.cfg.length_m)
        alpha_power_per_m = self.cfg.loss_db_per_m * _DB_TO_NEPER_POWER
        amp_half_linear = np.exp(0.25 * (g_power_per_m - alpha_power_per_m) * dz)
        linear_phase = np.exp(0.5j * self.cfg.beta2_s2_per_m * (w**2) * dz)

        evolved = field_t.copy()
        for _ in range(self.cfg.n_steps):
            evolved = _half_linear_step(
                evolved, linear_phase=linear_phase, amp_half_linear=amp_half_linear
            )
            p_t = np.abs(evolved) ** 2
            evolved = evolved * np.exp(1j * self.cfg.gamma_w_inv_m * dz * p_t)
            evolved = _half_linear_step(
                evolved, linear_phase=linear_phase, amp_half_linear=amp_half_linear
            )

        out.pulse.field_t = evolved
        out.pulse.field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(evolved)))
        out.pulse.intensity_t = np.abs(out.pulse.field_t) ** 2
        out.pulse.spectrum_w = np.abs(out.pulse.field_w) ** 2

        energy_out = _energy_au(out.pulse.field_t, dt=out.pulse.grid.dt)
        peak_out = float(np.max(out.pulse.intensity_t))
        bandwidth_out = _rms_bandwidth_rad_per_fs(w=w, spectrum=out.pulse.spectrum_w)
        b_integral_proxy = float(self.cfg.gamma_w_inv_m * self.cfg.length_m * peak_in)

        stage_metrics = {
            f"{self.name}.gain_db": float(self.cfg.gain_db),
            f"{self.name}.gain_linear": float(np.exp(g_power_per_m * self.cfg.length_m)),
            f"{self.name}.loss_db_per_m": float(self.cfg.loss_db_per_m),
            f"{self.name}.energy_in_au": energy_in,
            f"{self.name}.energy_out_au": energy_out,
            f"{self.name}.peak_power_in_au": peak_in,
            f"{self.name}.peak_power_out_au": peak_out,
            f"{self.name}.bandwidth_in_rad_per_fs": bandwidth_in,
            f"{self.name}.bandwidth_out_rad_per_fs": bandwidth_out,
            f"{self.name}.b_integral_proxy_rad": b_integral_proxy,
        }
        out.metrics.update(stage_metrics)
        out.artifacts.update(maybe_emit_stage_plots(stage_name=self.name, state=out, policy=policy))
        return StageResult(state=out, metrics=stage_metrics)


def _half_linear_step(
    field_t: np.ndarray,
    *,
    linear_phase: np.ndarray,
    amp_half_linear: float,
) -> np.ndarray:
    field_w = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(field_t)))
    field_w = field_w * linear_phase * amp_half_linear
    return np.fft.fftshift(np.fft.ifft(np.fft.ifftshift(field_w)))


def _energy_au(field_t: np.ndarray, *, dt: float) -> float:
    return float(np.sum(np.abs(field_t) ** 2) * dt)


def _power_gain_coeff_per_m(gain_db: float, length_m: float) -> float:
    gain_linear = 10 ** (gain_db / 10.0)
    return float(np.log(gain_linear) / length_m)


def _rms_bandwidth_rad_per_fs(w: np.ndarray, spectrum: np.ndarray) -> float:
    total = float(np.sum(spectrum))
    if total <= 0.0:
        return 0.0
    mean = float(np.sum(w * spectrum) / total)
    centered = (w - mean) ** 2
    return float(np.sqrt(np.sum(centered * spectrum) / total))
