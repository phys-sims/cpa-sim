from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cpa_sim.models import (
    PipelineConfig,
    RuntimeCfg,
    LaserGenCfg,
    ToyFiberAmpCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.models.config import recommended_n_samples_for_pulse, validate_pulse_sampling
from cpa_sim.models.state import BeamSpec, LaserSpec, PulseSpec
from cpa_sim.pipeline import run_pipeline
from cpa_sim.specs.mapping import LaserPulseWidthMapping, map_laser_pulse_width_to_sim_width
from specs.schema import (
    AmpSpecRecord,
    FiberSpecRecord,
    GratingSpecRecord,
    LaserSpecRecord,
    load_catalog,
)

DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-ab")

CATALOG_IDS = {
    "laser": "pritel_uoc_1550_ultrafast_optical_clock",
    "amp": "calmar_coronado_benchtop_edfa_1550",
    "fiber": "thorlabs_pmdcf_1550",
    "grating": "wasatch_wp_600lmm_1550_vph_50p8",
}

TARGET_AMP_POWER_W = 5.0
AMP_LENGTH_M = 1.5
AMP_GAMMA_W_INV_M = 4e-3
STRETCHER_LENGTH_M = 100.0
COMPRESSOR_SEPARATION_UM = 120_000.0


def _as_float(value: Any) -> float:
    return float(value)


def _metric_by_suffix(metrics: dict[str, Any], suffix: str) -> float | None:
    for key, value in metrics.items():
        if key.endswith(suffix):
            return value
    return None


def _observable_value(observables: dict[str, Any], measurement_name: str) -> float | None:
    for measurement in observables.get("measurements", []):
        if measurement.get("name") == measurement_name:
            value = measurement.get("value")
            return float(value) if isinstance(value, (float, int)) else None
    return None


def _stage_metric(metrics: dict[str, Any], *, stage_name: str, metric_name: str) -> float | None:
    key = f"cpa.{stage_name}.{stage_name}.{metric_name}"
    value = metrics.get(key)
    return float(value) if isinstance(value, (float, int)) else None


def _extract_comparison_metrics(
    metrics: dict[str, Any], observables: dict[str, Any]
) -> dict[str, float | None]:
    return {
        "energy_in_au": _stage_metric(metrics, stage_name="edfa", metric_name="energy_in_au"),
        "energy_out_au": _stage_metric(metrics, stage_name="edfa", metric_name="energy_out_au"),
        "energy_in_j": _stage_metric(metrics, stage_name="edfa", metric_name="energy_in_j"),
        "energy_out_j": _stage_metric(metrics, stage_name="edfa", metric_name="energy_out_j"),
        "power_in_avg_w": _stage_metric(metrics, stage_name="edfa", metric_name="power_in_avg_w"),
        "power_out_avg_w": _stage_metric(metrics, stage_name="edfa", metric_name="power_out_avg_w"),
        "peak_power_in_w": _stage_metric(metrics, stage_name="edfa", metric_name="peak_power_in_w"),
        "peak_power_out_w": _stage_metric(
            metrics, stage_name="edfa", metric_name="peak_power_out_w"
        ),
        "bandwidth_in_rad_per_fs": _stage_metric(
            metrics, stage_name="edfa", metric_name="bandwidth_in_rad_per_fs"
        ),
        "bandwidth_out_rad_per_fs": _stage_metric(
            metrics, stage_name="edfa", metric_name="bandwidth_out_rad_per_fs"
        ),
        "b_integral_proxy_rad": _stage_metric(
            metrics, stage_name="edfa", metric_name="b_integral_proxy_rad"
        ),
        "pipeline.final_energy_au": _metric_by_suffix(metrics, ".summary.energy_au"),
        "pipeline.final_peak_power_au": _metric_by_suffix(metrics, ".summary.peak_intensity_au"),
        "pipeline.final_bandwidth_rad_per_fs": _metric_by_suffix(
            metrics, ".summary.bandwidth_rad_per_fs"
        ),
        "pipeline.observable_fwhm_fs": _observable_value(observables, "intensity_fwhm"),
        "pipeline.observable_ac_fwhm_fs": _observable_value(
            observables, "intensity_autocorrelation_fwhm"
        ),
        "pipeline.observable_spectral_rms_rad_per_fs": _observable_value(
            observables, "spectral_rms_width"
        ),
    }


def _load_catalog_records() -> tuple[
    LaserSpecRecord, AmpSpecRecord, FiberSpecRecord, GratingSpecRecord
]:
    catalog = load_catalog()
    laser = catalog[CATALOG_IDS["laser"]]
    amp = catalog[CATALOG_IDS["amp"]]
    fiber = catalog[CATALOG_IDS["fiber"]]
    grating = catalog[CATALOG_IDS["grating"]]

    assert isinstance(laser, LaserSpecRecord)
    assert isinstance(amp, AmpSpecRecord)
    assert isinstance(fiber, FiberSpecRecord)
    assert isinstance(grating, GratingSpecRecord)
    return laser, amp, fiber, grating


def _build_laser_gen(laser_record: LaserSpecRecord) -> tuple[LaserGenCfg, LaserPulseWidthMapping]:
    operating_point = laser_record.model_extra["example_operating_point_for_sim_demo"]
    pulse_shape = str(operating_point["modeling_assumptions"]["pulse_intensity_shape"]).strip()
    mapped_shape: Literal["gaussian", "sech2"]
    if pulse_shape == "sech^2":
        mapped_shape = "sech2"
    elif pulse_shape == "gaussian":
        mapped_shape = "gaussian"
    else:
        raise ValueError(f"Unsupported pulse_intensity_shape for mapping: {pulse_shape!r}")
    width_mapping = map_laser_pulse_width_to_sim_width(
        source_width_ps=float(operating_point["pulsewidth_fwhm_ps"]),
        source_measurement_type="autocorrelation_fwhm",
        assumed_pulse_shape=mapped_shape,
        uncertainty_rel=0.15,
        assumptions=[
            f"Catalog operating point source: laser record {laser_record.id}",
            "Vendor pulsewidth is interpreted as autocorrelation FWHM for this demo mapping.",
        ],
    )

    time_window_fs = 120_000.0
    pulse = PulseSpec(
        shape=mapped_shape,
        amplitude=1.0,
        width_fs=width_mapping.simulation_width_fs,
        center_wavelength_nm=float(operating_point["center_wavelength_nm"]),
        rep_rate_mhz=float(operating_point["repetition_rate_hz"]) / 1e6,
        n_samples=recommended_n_samples_for_pulse(
            width_fs=width_mapping.simulation_width_fs,
            time_window_fs=time_window_fs,
            min_points_per_fwhm=24,
        ),
        time_window_fs=time_window_fs,
    )
    validate_pulse_sampling(pulse, strict=True)
    return LaserGenCfg(
        name=f"laser_init_{laser_record.id}",
        spec=LaserSpec(
            pulse=pulse,
            beam=BeamSpec(radius_mm=1.0, m2=1.0),
        ),
    ), width_mapping


def _build_shared_amp_stage() -> ToyFiberAmpCfg:
    return ToyFiberAmpCfg(
        name="edfa",
        length_m=AMP_LENGTH_M,
        beta2_s2_per_m=0.0,
        gamma_w_inv_m=AMP_GAMMA_W_INV_M,
        amp_power_w=TARGET_AMP_POWER_W,
        loss_db_per_m=0.0,
        n_steps=20,
    )


def _build_stretcher_stage(fiber_record: FiberSpecRecord) -> ToyFiberAmpCfg:
    gvd_raw = fiber_record.specs["dispersion"]["group_velocity_dispersion_fs2_per_m"]["value"]
    beta2_s2_per_m = _as_float(gvd_raw) * 1e-30
    loss_db_per_m = float(fiber_record.normalized["loss_db_per_m"]["value_db_per_m"])
    return ToyFiberAmpCfg(
        name="stretcher_fiber",
        length_m=STRETCHER_LENGTH_M,
        beta2_s2_per_m=beta2_s2_per_m,
        gamma_w_inv_m=0.0,
        amp_power_w=1e-6,
        loss_db_per_m=loss_db_per_m,
        n_steps=24,
    )


def _build_case_a_config(*, seed: int, laser_gen: LaserGenCfg) -> PipelineConfig:
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=laser_gen,
        stages=[_build_shared_amp_stage()],
    )


def _build_case_b_config(
    *,
    seed: int,
    laser_gen: LaserGenCfg,
    fiber_record: FiberSpecRecord,
    grating_record: GratingSpecRecord,
) -> PipelineConfig:
    line_density_lpmm = float(grating_record.specs["spatial_frequency_lines_per_mm"]["value"])
    incidence_angle_deg = float(grating_record.specs["angle_of_incidence_deg"]["value"])
    wavelength_nm = float(grating_record.specs["center_wavelength_nm"])
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=laser_gen,
        stages=[
            _build_stretcher_stage(fiber_record),
            _build_shared_amp_stage(),
            TreacyGratingPairCfg(
                name="compressor",
                line_density_lpmm=line_density_lpmm,
                incidence_angle_deg=incidence_angle_deg,
                separation_um=COMPRESSOR_SEPARATION_UM,
                wavelength_nm=wavelength_nm,
                n_passes=2,
                include_tod=True,
                apply_to_pulse=True,
            ),
        ],
    )


def _run_case(
    *,
    case_name: str,
    description: str,
    cfg: PipelineConfig,
    out_dir: Path,
    emit_plots: bool,
    width_mapping: LaserPulseWidthMapping,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    assumptions_path = out_dir / "laser_measurement_assumptions.json"
    assumptions_path.write_text(json.dumps(width_mapping.model_dump(mode="json"), indent=2) + "\n")

    policy = {
        "cpa.emit_stage_plots": emit_plots,
        "cpa.stage_plot_dir": str(out_dir / "stage-plots"),
    }
    result = run_pipeline(cfg, policy=policy)
    observables = result.state.meta.get("observable_contract", {})
    payload = {
        "matching_criterion": "output_energy",
        "description": description,
        "comparison_metrics": _extract_comparison_metrics(result.metrics, observables),
        "metrics": result.metrics,
        "observables": observables,
        "assumptions": {
            "laser_measurement_model": width_mapping.model_dump(mode="json"),
        },
        "artifacts": {
            **result.artifacts,
            **result.state.artifacts,
            "cpa.assumptions.laser_measurement_model": str(assumptions_path),
        },
        "metadata": {
            **result.state.meta,
            "assumptions": {
                "laser_measurement_model": width_mapping.model_dump(mode="json"),
            },
        },
    }
    (out_dir / "run_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return {
        "name": case_name,
        "description": description,
        "summary_path": str(out_dir / "run_summary.json"),
        "comparison_metrics": payload["comparison_metrics"],
    }


def run_comparison(*, out_dir: Path, seed: int, emit_plots: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    laser_record, amp_record, fiber_record, grating_record = _load_catalog_records()
    laser_gen, width_mapping = _build_laser_gen(laser_record)

    case_a = _run_case(
        case_name="A_direct",
        description="Catalog 2 ps seed pulse -> EDFA (5 W target) -> metrics.",
        cfg=_build_case_a_config(seed=seed, laser_gen=laser_gen),
        out_dir=out_dir / "case-a",
        emit_plots=emit_plots,
        width_mapping=width_mapping,
    )
    case_b = _run_case(
        case_name="B_cpa",
        description="Catalog 2 ps seed -> PMDCF stretcher -> EDFA (5 W target) -> Treacy compressor.",
        cfg=_build_case_b_config(
            seed=seed,
            laser_gen=laser_gen,
            fiber_record=fiber_record,
            grating_record=grating_record,
        ),
        out_dir=out_dir / "case-b",
        emit_plots=emit_plots,
        width_mapping=width_mapping,
    )

    comparison = {
        "seed": seed,
        "laser_gen": {
            "source": f"catalog:{laser_record.id}",
            "shared_spec": {
                "name": laser_gen.name,
                "width_fs": laser_gen.spec.pulse.width_fs,
                "center_wavelength_nm": laser_gen.spec.pulse.center_wavelength_nm,
                "rep_rate_hz": laser_gen.spec.pulse.rep_rate_mhz * 1e6,
            },
            "measurement_mapping": width_mapping.model_dump(mode="json"),
        },
        "catalog": {
            "laser": laser_record.id,
            "amp": amp_record.id,
            "fiber": fiber_record.id,
            "grating": grating_record.id,
        },
        "shared_amp": {
            "name": "edfa",
            "kind": "toy_fiber_amp",
            "catalog_source": amp_record.id,
            "length_m": AMP_LENGTH_M,
            "gamma_w_inv_m": AMP_GAMMA_W_INV_M,
            "amp_power_w": TARGET_AMP_POWER_W,
        },
        "cases": {
            case_a["name"]: {
                "description": case_a["description"],
                "summary_path": case_a["summary_path"],
                "comparison_metrics": case_a["comparison_metrics"],
            },
            case_b["name"]: {
                "description": case_b["description"],
                "summary_path": case_b["summary_path"],
                "comparison_metrics": case_b["comparison_metrics"],
            },
        },
    }

    (out_dir / "comparison_summary.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n"
    )
    return comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run toy amp A vs B comparison with a shared amp stage configuration."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--emit-plots", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    comparison = run_comparison(
        out_dir=args.out,
        seed=args.seed,
        emit_plots=args.emit_plots,
    )
    print(f"wrote comparison: {args.out / 'comparison_summary.json'}")
    print(f"compared metrics: {len(comparison['cases']['A_direct']['comparison_metrics'])}")


if __name__ == "__main__":
    main()
