from __future__ import annotations

from pathlib import Path

import numpy as np

from cpa_sim.models.config import LaserGenCfg, PhaseOnlyDispersionCfg, TreacyGratingPairCfg
from cpa_sim.models.state import BeamState, LaserSpec, LaserState, PulseGrid, PulseSpec, PulseState
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.plotting.common import LineSeries, autoscale_window_1d, plot_line_series
from cpa_sim.stages.free_space.treacy_grating import (
    TreacyGratingStage,
    _compute_treacy_metrics,
    _phase_from_dispersion,
)
from cpa_sim.stages.laser_gen.analytic import AnalyticLaserGenStage

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "treacy_validation"
LIGHT_SPEED_M_PER_S = 299_792_458.0
ENABLE_ABSOLUTE_OMEGA_PLOTS = False


def _empty_state() -> LaserState:
    pulse = PulseState(
        grid=PulseGrid(t=[0.0, 1.0], w=[0.0, 1.0], dt=1.0, dw=1.0, center_wavelength_nm=1030.0),
        field_t=np.zeros(2, dtype=np.complex128),
        field_w=np.zeros(2, dtype=np.complex128),
        intensity_t=np.zeros(2),
        spectrum_w=np.zeros(2),
    )
    return LaserState(
        pulse=pulse,
        beam=BeamState(radius_mm=1.0, m2=1.0),
        meta={},
        metrics={},
        artifacts={},
    )


def _run_stage(state: LaserState, cfg: PhaseOnlyDispersionCfg | TreacyGratingPairCfg) -> LaserState:
    result: StageResult[LaserState] = TreacyGratingStage(cfg).process(state)
    return result.state


def _rms_duration_fs(t_fs: np.ndarray, intensity: np.ndarray) -> float:
    weight = np.maximum(np.asarray(intensity, dtype=float), 0.0)
    t_arr = np.asarray(t_fs, dtype=float)
    norm = np.trapezoid(weight, t_arr)
    if norm <= 0.0:
        return float("nan")
    t_mean = np.trapezoid(t_arr * weight, t_arr) / norm
    variance = np.trapezoid(((t_arr - t_mean) ** 2) * weight, t_arr) / norm
    return float(np.sqrt(max(variance, 0.0)))


def _derivatives(
    phi_values: np.ndarray,
    domega_rad_per_fs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dphi = np.gradient(phi_values, domega_rad_per_fs)
    d2phi = np.gradient(dphi, domega_rad_per_fs)
    d3phi = np.gradient(d2phi, domega_rad_per_fs)
    return dphi, d2phi, d3phi


def _recover_gdd_tod(
    domega_rad_per_fs: np.ndarray,
    d2phi: np.ndarray,
    d3phi: np.ndarray,
) -> tuple[float, float]:
    center_mask = np.abs(domega_rad_per_fs) <= 0.7 * np.max(np.abs(domega_rad_per_fs))
    gdd_est = float(np.mean(d2phi[center_mask]))
    tod_est = float(np.mean(d3phi[center_mask]))
    return gdd_est, tod_est


def _normalized_correlation(a: np.ndarray, b: np.ndarray) -> float:
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    a_centered = a_arr - np.mean(a_arr)
    b_centered = b_arr - np.mean(b_arr)
    denom = float(np.linalg.norm(a_centered) * np.linalg.norm(b_centered))
    if denom == 0.0:
        return 1.0
    return float(np.dot(a_centered, b_centered) / denom)


def _relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(b_arr))
    if denom == 0.0:
        return float(np.linalg.norm(a_arr - b_arr))
    return float(np.linalg.norm(a_arr - b_arr) / denom)


def _expected_d2phi_curve(
    domega_rad_per_fs: np.ndarray,
    *,
    gdd_fs2: float,
    tod_fs3: float,
) -> np.ndarray:
    # With phi(Delta omega)=0.5*GDD*Delta omega^2 + (1/6)*TOD*Delta omega^3:
    # d2phi/d(Delta omega)^2 = GDD + TOD*Delta omega.
    return float(gdd_fs2) + float(tod_fs3) * np.asarray(domega_rad_per_fs, dtype=float)


def _series_with_window(
    *,
    x: np.ndarray,
    reference_values: np.ndarray,
    series: list[LineSeries],
    threshold_fraction: float,
    span_multiplier: float = 1.0,
) -> list[LineSeries]:
    x_arr = np.asarray(x, dtype=float)
    xlim = autoscale_window_1d(
        x_axis=x_arr,
        values=np.asarray(reference_values, dtype=float),
        threshold_fraction=threshold_fraction,
    )
    if xlim is None:
        return series

    lo, hi = xlim
    if span_multiplier > 1.0:
        center = 0.5 * (lo + hi)
        half_span = 0.5 * (hi - lo) * span_multiplier
        lo = center - half_span
        hi = center + half_span

    mask = (x_arr >= lo) & (x_arr <= hi)
    if np.count_nonzero(mask) < 2:
        return series

    return [
        LineSeries(
            x=np.asarray(entry.x, dtype=float)[mask],
            y=np.asarray(entry.y, dtype=float)[mask],
            label=entry.label,
        )
        for entry in series
    ]


def _absolute_omega_axis_rad_per_fs(state: LaserState) -> np.ndarray:
    center_wavelength_nm = float(state.pulse.grid.center_wavelength_nm)
    omega0_rad_per_s = 2.0 * np.pi * LIGHT_SPEED_M_PER_S / (center_wavelength_nm * 1e-9)
    return np.asarray(state.pulse.grid.w, dtype=float) + omega0_rad_per_s * 1e-15


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
    domega = np.asarray(initial_state.pulse.grid.w, dtype=float)
    t_fs = np.asarray(initial_state.pulse.grid.t, dtype=float)
    input_spectrum = np.asarray(initial_state.pulse.spectrum_w, dtype=float)
    input_intensity = np.asarray(initial_state.pulse.intensity_t, dtype=float)

    # Section 1: generic phase-only polynomial demo (hand-picked coefficients).
    poly_gdd_cfg = PhaseOnlyDispersionCfg(name="poly_gdd", gdd_fs2=8.5e4, tod_fs3=0.0)
    poly_gdd_tod_cfg = PhaseOnlyDispersionCfg(name="poly_gdd_tod", gdd_fs2=8.5e4, tod_fs3=1.8e5)
    poly_recompress_cfg = PhaseOnlyDispersionCfg(
        name="poly_recompress",
        gdd_fs2=-poly_gdd_cfg.gdd_fs2,
        tod_fs3=-poly_gdd_cfg.tod_fs3,
    )

    poly_gdd_state = _run_stage(initial_state, poly_gdd_cfg)
    poly_gdd_tod_state = _run_stage(initial_state, poly_gdd_tod_cfg)
    poly_recompressed_state = _run_stage(poly_gdd_state, poly_recompress_cfg)

    phi_poly_gdd = _phase_from_dispersion(
        domega,
        gdd_fs2=poly_gdd_cfg.gdd_fs2,
        tod_fs3=poly_gdd_cfg.tod_fs3,
    )
    phi_poly_gdd_tod = _phase_from_dispersion(
        domega,
        gdd_fs2=poly_gdd_tod_cfg.gdd_fs2,
        tod_fs3=poly_gdd_tod_cfg.tod_fs3,
    )

    tau_poly_gdd, d2_poly_gdd, d3_poly_gdd = _derivatives(phi_poly_gdd, domega)
    tau_poly_gdd_tod, d2_poly_gdd_tod, d3_poly_gdd_tod = _derivatives(phi_poly_gdd_tod, domega)
    expected_d2_poly_gdd = _expected_d2phi_curve(
        domega,
        gdd_fs2=poly_gdd_cfg.gdd_fs2,
        tod_fs3=poly_gdd_cfg.tod_fs3,
    )
    expected_d2_poly_gdd_tod = _expected_d2phi_curve(
        domega,
        gdd_fs2=poly_gdd_tod_cfg.gdd_fs2,
        tod_fs3=poly_gdd_tod_cfg.tod_fs3,
    )
    gdd_est_poly_gdd, tod_est_poly_gdd = _recover_gdd_tod(domega, d2_poly_gdd, d3_poly_gdd)
    gdd_est_poly_gdd_tod, tod_est_poly_gdd_tod = _recover_gdd_tod(
        domega,
        d2_poly_gdd_tod,
        d3_poly_gdd_tod,
    )

    phase_series = _series_with_window(
        x=domega,
        reference_values=input_spectrum,
        threshold_fraction=2e-3,
        series=[
            LineSeries(x=domega, y=phi_poly_gdd, label="Hand-picked polynomial (GDD only)"),
            LineSeries(x=domega, y=phi_poly_gdd_tod, label="Hand-picked polynomial (GDD + TOD)"),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "phi_vs_w.png",
        series=phase_series,
        x_label="Delta omega [rad/fs]",
        y_label="phi(Delta omega) [rad]",
        title="Generic Polynomial Demo: Spectral Phase on Offset-Frequency Grid",
        figsize=(9, 5),
    )

    group_delay_series = _series_with_window(
        x=domega,
        reference_values=input_spectrum,
        threshold_fraction=2e-3,
        series=[
            LineSeries(x=domega, y=tau_poly_gdd, label="dphi/d(Delta omega), GDD only"),
            LineSeries(x=domega, y=tau_poly_gdd_tod, label="dphi/d(Delta omega), GDD + TOD"),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "group_delay_vs_w.png",
        series=group_delay_series,
        x_label="Delta omega [rad/fs]",
        y_label="dphi/d(Delta omega) [fs]",
        title="Generic Polynomial Demo: Group Delay",
        figsize=(9, 5),
    )

    d2phi_series = _series_with_window(
        x=domega,
        reference_values=input_spectrum,
        threshold_fraction=2e-3,
        series=[
            LineSeries(x=domega, y=d2_poly_gdd, label="Numerical d2phi, GDD only"),
            LineSeries(x=domega, y=expected_d2_poly_gdd, label="Expected d2phi = GDD"),
            LineSeries(x=domega, y=d2_poly_gdd_tod, label="Numerical d2phi, GDD + TOD"),
            LineSeries(
                x=domega,
                y=expected_d2_poly_gdd_tod,
                label="Expected d2phi = GDD + TOD*Delta omega",
            ),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "d2phi_vs_w.png",
        series=d2phi_series,
        x_label="Delta omega [rad/fs]",
        y_label="d2phi/d(Delta omega)^2 [fs^2]",
        title="Generic Polynomial Demo: Second Derivative Validation",
        figsize=(9, 5),
    )

    time_window_series = _series_with_window(
        x=t_fs,
        reference_values=input_intensity,
        threshold_fraction=3e-3,
        span_multiplier=6.0,
        series=[
            LineSeries(x=t_fs, y=input_intensity, label="Input"),
            LineSeries(
                x=t_fs, y=poly_gdd_state.pulse.intensity_t, label="After hand-picked stretcher"
            ),
            LineSeries(
                x=t_fs,
                y=poly_recompressed_state.pulse.intensity_t,
                label="After matched polynomial recompressor",
            ),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "intensity_time_before_after.png",
        series=time_window_series,
        x_label="t [fs]",
        y_label="|E(t)|^2 [a.u.]",
        title="Generic Polynomial Demo: Stretch and Recompression in Time Domain",
        figsize=(9, 5),
    )

    spectrum_series = _series_with_window(
        x=domega,
        reference_values=input_spectrum,
        threshold_fraction=2e-3,
        series=[
            LineSeries(x=domega, y=input_spectrum, label="Input"),
            LineSeries(
                x=domega,
                y=poly_gdd_state.pulse.spectrum_w,
                label="After hand-picked stretcher",
            ),
            LineSeries(
                x=domega,
                y=poly_recompressed_state.pulse.spectrum_w,
                label="After matched polynomial recompressor",
            ),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "spectrum_before_after.png",
        series=spectrum_series,
        x_label="Delta omega [rad/fs]",
        y_label="|E(Delta omega)|^2 [a.u.]",
        title="Generic Polynomial Demo: Spectral Magnitude Invariance (Phase-Only)",
        figsize=(9, 5),
    )

    if ENABLE_ABSOLUTE_OMEGA_PLOTS:
        omega_abs = _absolute_omega_axis_rad_per_fs(initial_state)
        absolute_phase_series = _series_with_window(
            x=omega_abs,
            reference_values=input_spectrum,
            threshold_fraction=2e-3,
            series=[
                LineSeries(
                    x=omega_abs,
                    y=phi_poly_gdd_tod,
                    label="Same polynomial phase, re-plotted vs absolute omega",
                )
            ],
        )
        plot_line_series(
            out_path=ASSET_DIR / "optional_phi_vs_absolute_omega.png",
            series=absolute_phase_series,
            x_label="Absolute optical omega [rad/fs]",
            y_label="phi(omega) [rad]",
            title="Optional Reference Plot: Absolute Optical Omega Axis",
            figsize=(9, 5),
        )

    # Section 2: Treacy backend equivalence.
    # This is an implementation check, not independent physics validation.
    treacy_cfg = TreacyGratingPairCfg(
        name="treacy",
        line_density_lpmm=1200.0,
        incidence_angle_deg=34.0,
        separation_um=115_000.0,
        wavelength_nm=1030.0,
        include_tod=True,
        apply_to_pulse=True,
    )
    treacy_metrics = _compute_treacy_metrics(treacy_cfg)
    treacy_matched_poly_cfg = PhaseOnlyDispersionCfg(
        name="treacy_matched_phase_only",
        gdd_fs2=treacy_metrics["gdd_fs2"],
        tod_fs3=treacy_metrics["tod_fs3"],
        apply_to_pulse=treacy_cfg.apply_to_pulse,
    )

    treacy_state = _run_stage(initial_state, treacy_cfg)
    treacy_matched_poly_state = _run_stage(initial_state, treacy_matched_poly_cfg)

    treacy_overlay_series = _series_with_window(
        x=t_fs,
        reference_values=input_intensity,
        threshold_fraction=3e-3,
        span_multiplier=6.0,
        series=[
            LineSeries(x=t_fs, y=treacy_state.pulse.intensity_t, label="TreacyGratingStage output"),
            LineSeries(
                x=t_fs,
                y=treacy_matched_poly_state.pulse.intensity_t,
                label="PhaseOnlyDispersionCfg output (matched Treacy coefficients)",
            ),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "treacy_vs_poly_intensity_overlay.png",
        series=treacy_overlay_series,
        x_label="t [fs]",
        y_label="|E(t)|^2 [a.u.]",
        title="Treacy Backend Equivalence: Time-Domain Overlay (Like-for-Like)",
        figsize=(9, 5),
    )

    treacy_spectrum_overlay_series = _series_with_window(
        x=domega,
        reference_values=input_spectrum,
        threshold_fraction=2e-3,
        series=[
            LineSeries(
                x=domega,
                y=treacy_state.pulse.spectrum_w,
                label="TreacyGratingStage spectrum",
            ),
            LineSeries(
                x=domega,
                y=treacy_matched_poly_state.pulse.spectrum_w,
                label="PhaseOnlyDispersionCfg spectrum (matched coefficients)",
            ),
        ],
    )
    plot_line_series(
        out_path=ASSET_DIR / "treacy_vs_poly_spectrum_overlay.png",
        series=treacy_spectrum_overlay_series,
        x_label="Delta omega [rad/fs]",
        y_label="|E(Delta omega)|^2 [a.u.]",
        title="Treacy Backend Equivalence: Spectrum Overlay (Like-for-Like)",
        figsize=(9, 5),
    )

    rms_input = _rms_duration_fs(t_fs, input_intensity)
    rms_poly_stretched = _rms_duration_fs(t_fs, poly_gdd_state.pulse.intensity_t)
    rms_poly_recompressed = _rms_duration_fs(t_fs, poly_recompressed_state.pulse.intensity_t)
    rms_poly_gdd_tod = _rms_duration_fs(t_fs, poly_gdd_tod_state.pulse.intensity_t)
    rms_treacy = _rms_duration_fs(t_fs, treacy_state.pulse.intensity_t)
    rms_treacy_matched = _rms_duration_fs(t_fs, treacy_matched_poly_state.pulse.intensity_t)

    treacy_time_corr = _normalized_correlation(
        np.asarray(treacy_state.pulse.intensity_t, dtype=float),
        np.asarray(treacy_matched_poly_state.pulse.intensity_t, dtype=float),
    )
    treacy_time_rel_l2 = _relative_l2(
        np.asarray(treacy_state.pulse.intensity_t, dtype=float),
        np.asarray(treacy_matched_poly_state.pulse.intensity_t, dtype=float),
    )
    treacy_spectrum_rel_l2 = _relative_l2(
        np.asarray(treacy_state.pulse.spectrum_w, dtype=float),
        np.asarray(treacy_matched_poly_state.pulse.spectrum_w, dtype=float),
    )
    treacy_rms_rel_diff = abs(rms_treacy - rms_treacy_matched) / max(abs(rms_treacy_matched), 1e-12)

    print("Treacy stage validation summary")
    print("-------------------------------")
    print("1) Generic phase-only polynomial demo (hand-picked coefficients)")
    print(f"RMS duration input                     : {rms_input:10.4f} fs")
    print(f"RMS duration stretched (GDD only)      : {rms_poly_stretched:10.4f} fs")
    print(f"RMS duration recompressed              : {rms_poly_recompressed:10.4f} fs")
    print(f"RMS duration stretched (GDD + TOD)     : {rms_poly_gdd_tod:10.4f} fs")
    print(
        "Recovered from derivatives (GDD-only)  : "
        f"GDD={gdd_est_poly_gdd:.3f} fs^2, TOD={tod_est_poly_gdd:.3f} fs^3"
    )
    print(
        "Recovered from derivatives (GDD+TOD)   : "
        f"GDD={gdd_est_poly_gdd_tod:.3f} fs^2, TOD={tod_est_poly_gdd_tod:.3f} fs^3"
    )
    print()
    print("2) Treacy backend equivalence (same coefficients; implementation check only)")
    print(
        "Treacy coefficients from geometry      : "
        f"GDD={treacy_metrics['gdd_fs2']:.3f} fs^2, TOD={treacy_metrics['tod_fs3']:.3f} fs^3"
    )
    print(f"RMS duration Treacy stage              : {rms_treacy:10.4f} fs")
    print(f"RMS duration matched phase-only stage  : {rms_treacy_matched:10.4f} fs")
    print(f"Time-domain correlation                : {treacy_time_corr:10.6f}")
    print(f"Time-domain relative L2 difference     : {treacy_time_rel_l2:10.6e}")
    print(f"Spectrum relative L2 difference        : {treacy_spectrum_rel_l2:10.6e}")
    print(f"RMS relative difference                : {treacy_rms_rel_diff:10.6e}")
    print()
    print(f"Artifacts written to: {ASSET_DIR}")


if __name__ == "__main__":
    main()
