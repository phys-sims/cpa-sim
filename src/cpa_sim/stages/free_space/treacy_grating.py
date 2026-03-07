from __future__ import annotations

import math

import numpy as np

from cpa_sim.grid_contract import assert_offset_omega_grid
from cpa_sim.models.config import (
    FreeSpaceCfg,
    PhaseOnlyDispersionCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import PolicyBag, StageResult
from cpa_sim.physics.windowing import run_with_auto_window
from cpa_sim.stages.base import LaserStage
from cpa_sim.utils import maybe_emit_stage_plots

C_UM_PER_FS = 0.299792458


def _phase_from_dispersion(
    domega_rad_per_fs: np.ndarray,
    gdd_fs2: float,
    tod_fs3: float,
) -> np.ndarray:
    """Evaluate polynomial dispersion phase on an offset-frequency (Δω) grid.

    In this envelope-model simulator, ``PulseGrid.w`` is already a carrier-offset axis
    (Δω). Dispersion polynomials are applied directly on this Δω grid (about Δω≈0),
    not by subtracting ``ω0_optical`` or re-centering with ``mean(w)``.
    """

    phase = -0.5 * gdd_fs2 * domega_rad_per_fs**2
    if tod_fs3 != 0.0:
        phase -= (1.0 / 6.0) * tod_fs3 * domega_rad_per_fs**3
    return phase


def _safe_asin(arg: float, *, context: str) -> float:
    if arg < -1.0 or arg > 1.0:
        raise ValueError(
            f"Invalid asin domain for {context}: arg={arg:.12g} (must be within [-1, 1])."
        )
    return math.asin(arg)


def _compute_treacy_metrics(cfg: TreacyGratingPairCfg) -> dict[str, float]:
    lambda_um = cfg.wavelength_nm * 1e-3
    d_um = 1000.0 / cfg.line_density_lpmm
    theta_i_rad = math.radians(cfg.incidence_angle_deg)
    m = float(cfg.diffraction_order)
    n_passes = float(cfg.n_passes)
    L_um = cfg.separation_um

    littrow_arg = lambda_um / (2.0 * d_um)
    theta_l_rad = _safe_asin(littrow_arg, context="littrow angle")

    diff_arg = -m * (lambda_um / d_um) - math.sin(theta_i_rad)
    theta_d_rad = _safe_asin(diff_arg, context="diffraction angle")

    gdd_bracket = 1.0 - (-m * lambda_um / d_um - math.sin(theta_i_rad)) ** 2
    if gdd_bracket <= 0.0:
        raise ValueError(
            "Invalid Treacy geometry: GDD radical argument must be > 0. "
            f"Got {gdd_bracket:.12g} with line_density_lpmm={cfg.line_density_lpmm}, "
            f"incidence_angle_deg={cfg.incidence_angle_deg}, wavelength_nm={cfg.wavelength_nm}, "
            f"diffraction_order={cfg.diffraction_order}."
        )
    gdd = -(
        (n_passes * m**2 * L_um * lambda_um**3) / (2.0 * math.pi * C_UM_PER_FS**2 * d_um**2)
    ) * gdd_bracket ** (-1.5)

    tod_den = 1.0 - ((lambda_um / d_um) - math.sin(theta_i_rad)) ** 2
    if tod_den <= 0.0:
        raise ValueError(
            "Invalid Treacy geometry: TOD denominator must be > 0. "
            f"Got {tod_den:.12g} with line_density_lpmm={cfg.line_density_lpmm}, "
            f"incidence_angle_deg={cfg.incidence_angle_deg}, wavelength_nm={cfg.wavelength_nm}."
        )
    tod_num = 1.0 + (lambda_um / d_um) * math.sin(theta_i_rad) - math.sin(theta_i_rad) ** 2
    tod = -((3.0 * lambda_um) / (2.0 * math.pi * C_UM_PER_FS)) * (tod_num / tod_den) * gdd

    omega0_rad_per_fs = 2.0 * math.pi * C_UM_PER_FS / lambda_um
    out_gdd = cfg.override_gdd_fs2 if cfg.override_gdd_fs2 is not None else gdd
    computed_tod = tod if cfg.include_tod else 0.0
    out_tod = cfg.override_tod_fs3 if cfg.override_tod_fs3 is not None else computed_tod

    return {
        "gdd_fs2": float(out_gdd),
        "tod_fs3": float(out_tod),
        "line_density_lpmm": float(cfg.line_density_lpmm),
        "period_um": float(d_um),
        "wavelength_nm": float(cfg.wavelength_nm),
        "wavelength_um": float(lambda_um),
        "incidence_angle_deg": float(cfg.incidence_angle_deg),
        "incidence_angle_rad": float(theta_i_rad),
        "littrow_angle_deg": float(math.degrees(theta_l_rad)),
        "diffraction_angle_deg": float(math.degrees(theta_d_rad)),
        "omega0_rad_per_fs": float(omega0_rad_per_fs),
        "n_passes": float(cfg.n_passes),
        "diffraction_order": float(cfg.diffraction_order),
    }


class TreacyGratingStage(LaserStage[FreeSpaceCfg]):
    def __init__(self, cfg: FreeSpaceCfg):
        super().__init__(cfg)
        self.name = cfg.name

    def process(
        self, state: LaserState, *, policy: PolicyBag | None = None
    ) -> StageResult[LaserState]:
        w = np.asarray(state.pulse.grid.w)
        assert_offset_omega_grid(w)
        w_ref = 0.0

        if isinstance(self.cfg, TreacyGratingPairCfg):
            cfg_metrics = _compute_treacy_metrics(self.cfg)
            gdd_fs2 = cfg_metrics["gdd_fs2"]
            tod_fs3 = cfg_metrics["tod_fs3"]
            apply_to_pulse = self.cfg.apply_to_pulse
            omega0_optical_rad_per_fs = cfg_metrics["omega0_rad_per_fs"]
            cfg_metrics["omega0_optical_rad_per_fs"] = omega0_optical_rad_per_fs
            cfg_metrics["omega_ref_grid_rad_per_fs"] = w_ref
            cfg_metrics["omega_grid_mean_rad_per_fs"] = float(np.mean(w))
        else:
            assert isinstance(self.cfg, PhaseOnlyDispersionCfg)
            gdd_fs2 = float(self.cfg.gdd_fs2)
            tod_fs3 = float(self.cfg.tod_fs3)
            apply_to_pulse = self.cfg.apply_to_pulse
            cfg_metrics = {
                "gdd_fs2": gdd_fs2,
                "tod_fs3": tod_fs3,
                "omega0_rad_per_fs": w_ref,
                "omega_ref_grid_rad_per_fs": w_ref,
                "omega_grid_mean_rad_per_fs": float(np.mean(w)),
            }

        if apply_to_pulse:

            def _apply_once(state_in: LaserState) -> LaserState:
                out_state = state_in.deepcopy()
                domega = np.asarray(out_state.pulse.grid.w)
                assert_offset_omega_grid(domega)
                phase = _phase_from_dispersion(domega, gdd_fs2=gdd_fs2, tod_fs3=tod_fs3)
                out_state.pulse.field_w = out_state.pulse.field_w * np.exp(1j * phase)
                out_state.pulse.field_t = np.fft.fftshift(
                    np.fft.ifft(np.fft.ifftshift(out_state.pulse.field_w))
                )
                out_state.pulse.intensity_t = np.abs(out_state.pulse.field_t) ** 2
                out_state.pulse.spectrum_w = np.abs(out_state.pulse.field_w) ** 2
                return out_state

            out, aw_metrics, aw_events = run_with_auto_window(
                state,
                _apply_once,
                stage_name=self.name,
                policy=policy,
            )
            out.meta.setdefault("auto_window_events", [])
            out.meta["auto_window_events"].extend(aw_events)
        else:
            out = state.deepcopy()
            aw_metrics = {}

        stage_metrics = {
            f"{self.name}.energy_au": float(np.sum(out.pulse.intensity_t) * out.pulse.grid.dt),
            f"{self.name}.apply_to_pulse": float(1.0 if apply_to_pulse else 0.0),
        }
        stage_metrics.update({f"{self.name}.{key}": value for key, value in cfg_metrics.items()})
        stage_metrics[f"{self.name}.omega_grid_mean_rad_per_fs"] = float(
            np.mean(out.pulse.grid.w)
        )
        stage_metrics.update(aw_metrics)
        out.metrics.update(stage_metrics)
        out.artifacts.update(maybe_emit_stage_plots(stage_name=self.name, state=out, policy=policy))
        return StageResult(state=out, metrics=stage_metrics)
