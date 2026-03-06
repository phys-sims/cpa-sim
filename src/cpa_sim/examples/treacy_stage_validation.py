from __future__ import annotations

from pathlib import Path

import numpy as np

from cpa_sim.models.config import LaserGenCfg, PhaseOnlyDispersionCfg, TreacyGratingPairCfg
from cpa_sim.models.state import BeamState, LaserSpec, LaserState, PulseGrid, PulseSpec, PulseState
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.plotting.common import LineSeries, plot_line_series
from cpa_sim.stages.free_space.treacy_grating import (
    TreacyGratingStage,
    _compute_treacy_metrics,
    _phase_from_dispersion,
)
from cpa_sim.stages.laser_gen.analytic import AnalyticLaserGenStage

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "treacy_validation"


def _empty_state() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse, beam=BeamState(radius_mm=1.0, m2=1.0), meta={}, metrics={}, artifacts={}
    )


def _run_stage(state: LaserState, cfg: PhaseOnlyDispersionCfg | TreacyGratingPairCfg) -> LaserState:
    result: StageResult[LaserState] = TreacyGratingStage(cfg).process(state)
    return result.state


def _rms_duration_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    weight = np.maximum(intensity, 0.0)
    norm = np.trapezoid(weight, t_fs)
    if norm <= 0.0:
        return float("nan")
    t_mean = np.trapezoid(t_fs * weight, t_fs) / norm
    variance = np.trapezoid(((t_fs - t_mean) ** 2) * weight, t_fs) / norm
    return float(np.sqrt(max(variance, 0.0)))


def _derivatives(phi: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dphi = np.gradient(phi, w)
    d2phi = np.gradient(dphi, w)
    d3phi = np.gradient(d2phi, w)
    return dphi, d2phi, d3phi


def _recover_gdd_tod(w: np.ndarray, d2phi: np.ndarray, d3phi: np.ndarray) -> tuple[float, float]:
    center_mask = np.abs(w) <= 0.7 * np.max(np.abs(w))
    gdd_est = -float(np.mean(d2phi[center_mask]))
    tod_est = -float(np.mean(d3phi[center_mask]))
    return gdd_est, tod_est


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    laser_cfg = LaserGenCfg(
        name="laser",
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="gaussian",
                peak_power_w=1.0,
                width_fs=45.0,
                center_wavelength_nm=1030.0,
                n_samples=4096,
                time_window_fs=3000.0,
                rep_rate_mhz=1.0,
            )
        ),
    )
    initial_state = AnalyticLaserGenStage(laser_cfg).process(_empty_state()).state

    w = np.asarray(initial_state.pulse.grid.w)
    t = np.asarray(initial_state.pulse.grid.t)

    phase_gdd_cfg = PhaseOnlyDispersionCfg(name="phase_gdd", gdd_fs2=8.5e4, tod_fs3=0.0)
    phase_gdd_tod_cfg = PhaseOnlyDispersionCfg(name="phase_gdd_tod", gdd_fs2=8.5e4, tod_fs3=1.8e5)
    treacy_cfg = TreacyGratingPairCfg(
        name="treacy",
        line_density_lpmm=1200.0,
        incidence_angle_deg=34.0,
        separation_um=115_000.0,
        wavelength_nm=1030.0,
        include_tod=True,
    )

    phase_gdd_state = _run_stage(initial_state, phase_gdd_cfg)
    phase_gdd_tod_state = _run_stage(initial_state, phase_gdd_tod_cfg)
    treacy_state = _run_stage(initial_state, treacy_cfg)

    treacy_metrics = _compute_treacy_metrics(treacy_cfg)
    treacy_poly_cfg = PhaseOnlyDispersionCfg(
        name="treacy_poly",
        gdd_fs2=treacy_metrics["gdd_fs2"],
        tod_fs3=treacy_metrics["tod_fs3"],
    )
    treacy_poly_state = _run_stage(initial_state, treacy_poly_cfg)

    compressor_cfg = PhaseOnlyDispersionCfg(
        name="compressor", gdd_fs2=-phase_gdd_cfg.gdd_fs2, tod_fs3=-phase_gdd_cfg.tod_fs3
    )
    recompressed_state = _run_stage(phase_gdd_state, compressor_cfg)

    phi_gdd = _phase_from_dispersion(
        w, gdd_fs2=phase_gdd_cfg.gdd_fs2, tod_fs3=phase_gdd_cfg.tod_fs3
    )
    phi_gdd_tod = _phase_from_dispersion(
        w, gdd_fs2=phase_gdd_tod_cfg.gdd_fs2, tod_fs3=phase_gdd_tod_cfg.tod_fs3
    )
    phi_treacy = _phase_from_dispersion(
        w, gdd_fs2=treacy_metrics["gdd_fs2"], tod_fs3=treacy_metrics["tod_fs3"]
    )

    tau_g_gdd, d2_gdd, d3_gdd = _derivatives(phi_gdd, w)
    tau_g_gdd_tod, _, _ = _derivatives(phi_gdd_tod, w)
    tau_g_treacy, d2_treacy, d3_treacy = _derivatives(phi_treacy, w)

    gdd_est_gdd, tod_est_gdd = _recover_gdd_tod(w, d2_gdd, d3_gdd)
    gdd_est_treacy, tod_est_treacy = _recover_gdd_tod(w, d2_treacy, d3_treacy)

    plot_line_series(
        out_path=ASSET_DIR / "phi_vs_w.png",
        series=[
            LineSeries(x=w, y=phi_gdd, label="PhaseOnly (GDD)"),
            LineSeries(x=w, y=phi_gdd_tod, label="PhaseOnly (GDD+TOD)"),
            LineSeries(x=w, y=phi_treacy, label="Treacy mapped to polynomial"),
        ],
        x_label="Δω [rad/fs]",
        y_label="φ(Δω) [rad]",
        title="Spectral phase",
        figsize=(9, 5),
    )

    plot_line_series(
        out_path=ASSET_DIR / "group_delay_vs_w.png",
        series=[
            LineSeries(x=w, y=tau_g_gdd, label="PhaseOnly (GDD)"),
            LineSeries(x=w, y=tau_g_gdd_tod, label="PhaseOnly (GDD+TOD)"),
            LineSeries(x=w, y=tau_g_treacy, label="Treacy mapped to polynomial"),
        ],
        x_label="Δω [rad/fs]",
        y_label="dφ/dω [fs]",
        title="Group delay",
        figsize=(9, 5),
    )

    plot_line_series(
        out_path=ASSET_DIR / "d2phi_vs_w.png",
        series=[
            LineSeries(x=w, y=d2_gdd, label="PhaseOnly (GDD only)"),
            LineSeries(x=w, y=d2_treacy, label="Treacy (with TOD)"),
            LineSeries(x=w, y=np.full_like(w, -phase_gdd_cfg.gdd_fs2), label="Expected: -GDD"),
        ],
        x_label="Δω [rad/fs]",
        y_label="d²φ/dω² [fs²]",
        title="Second derivative of spectral phase",
        figsize=(9, 5),
    )

    plot_line_series(
        out_path=ASSET_DIR / "intensity_time_before_after.png",
        series=[
            LineSeries(x=t, y=initial_state.pulse.intensity_t, label="Input"),
            LineSeries(x=t, y=phase_gdd_state.pulse.intensity_t, label="After stretcher (GDD)"),
            LineSeries(x=t, y=recompressed_state.pulse.intensity_t, label="After compressor"),
        ],
        x_label="t [fs]",
        y_label="|E(t)|² [a.u.]",
        title="Time-domain intensity before/after stretcher/compressor",
        figsize=(9, 5),
    )

    plot_line_series(
        out_path=ASSET_DIR / "spectrum_before_after.png",
        series=[
            LineSeries(x=w, y=initial_state.pulse.spectrum_w, label="Input"),
            LineSeries(x=w, y=phase_gdd_state.pulse.spectrum_w, label="After stretcher"),
            LineSeries(x=w, y=recompressed_state.pulse.spectrum_w, label="After compressor"),
        ],
        x_label="Δω [rad/fs]",
        y_label="|E(Δω)|² [a.u.]",
        title="Spectrum before/after (phase-only invariance)",
        figsize=(9, 5),
    )

    plot_line_series(
        out_path=ASSET_DIR / "treacy_vs_poly_intensity_overlay.png",
        series=[
            LineSeries(x=t, y=treacy_state.pulse.intensity_t, label="TreacyGratingPair"),
            LineSeries(
                x=t,
                y=treacy_poly_state.pulse.intensity_t,
                label="PhaseOnly with Treacy GDD/TOD",
            ),
        ],
        x_label="t [fs]",
        y_label="|E(t)|² [a.u.]",
        title="Treacy vs polynomial phase-only overlay",
        figsize=(9, 5),
    )

    rms_in = _rms_duration_fs(t, initial_state.pulse.intensity_t)
    rms_stretched = _rms_duration_fs(t, phase_gdd_state.pulse.intensity_t)
    rms_recompressed = _rms_duration_fs(t, recompressed_state.pulse.intensity_t)
    rms_gdd_tod = _rms_duration_fs(t, phase_gdd_tod_state.pulse.intensity_t)
    rms_treacy = _rms_duration_fs(t, treacy_state.pulse.intensity_t)

    print("Treacy/phase-only validation summary")
    print("----------------------------------")
    print(f"RMS duration input           : {rms_in:10.4f} fs")
    print(f"RMS duration stretched (GDD) : {rms_stretched:10.4f} fs")
    print(f"RMS duration recompressed    : {rms_recompressed:10.4f} fs")
    print(f"RMS duration stretched (GDD+TOD): {rms_gdd_tod:10.4f} fs")
    print(f"RMS duration Treacy             : {rms_treacy:10.4f} fs")
    print(
        "Recovered from d²φ/dω²,d³φ/dω³ (GDD-only): "
        f"GDD={gdd_est_gdd:.3f} fs², TOD={tod_est_gdd:.3f} fs³"
    )
    print(
        "Recovered from d²φ/dω²,d³φ/dω³ (Treacy): "
        f"GDD={gdd_est_treacy:.3f} fs², TOD={tod_est_treacy:.3f} fs³"
    )
    print(
        "Treacy config coefficients: "
        f"GDD={treacy_metrics['gdd_fs2']:.3f} fs², TOD={treacy_metrics['tod_fs3']:.3f} fs³"
    )
    print(f"Artifacts written to: {ASSET_DIR}")


if __name__ == "__main__":
    main()
