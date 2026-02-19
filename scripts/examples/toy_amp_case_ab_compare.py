from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    PipelineConfig,
    RuntimeCfg,
    ToyFiberAmpCfg,
    TreacyGratingPairCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.pipeline import run_pipeline
from toy_amp_shared import build_shared_laser_gen, shared_laser_spec_summary

DEFAULT_OUT_DIR = Path("artifacts/toy-amp-case-ab")

# Shared toy amp used in both A (direct) and B (CPA) chains.
SHARED_AMP_KWARGS = {
    "name": "toy_amp",
    "length_m": 1.5,
    "beta2_s2_per_m": 0.0,
    "gamma_w_inv_m": 4e-3,
    "amp_power_w": 0.12,
    "loss_db_per_m": 0.0,
    "n_steps": 20,
}


def _metric_by_suffix(metrics: dict[str, Any], suffix: str) -> float | None:
    for key, value in metrics.items():
        if key.endswith(suffix):
            return value
    return None


def _extract_comparison_metrics(metrics: dict[str, Any]) -> dict[str, float | None]:
    return {
        "energy_in_au": _metric_by_suffix(metrics, ".energy_in_au"),
        "energy_out_au": _metric_by_suffix(metrics, ".energy_out_au"),
        "power_in_avg_w": _metric_by_suffix(metrics, ".power_in_avg_w"),
        "power_out_avg_w": _metric_by_suffix(metrics, ".power_out_avg_w"),
        "peak_power_in_au": _metric_by_suffix(metrics, ".peak_power_in_au"),
        "peak_power_out_au": _metric_by_suffix(metrics, ".peak_power_out_au"),
        "bandwidth_in_rad_per_fs": _metric_by_suffix(metrics, ".bandwidth_in_rad_per_fs"),
        "bandwidth_out_rad_per_fs": _metric_by_suffix(metrics, ".bandwidth_out_rad_per_fs"),
        "b_integral_proxy_rad": _metric_by_suffix(metrics, ".b_integral_proxy_rad"),
        "pipeline.final_energy_au": _metric_by_suffix(metrics, ".summary.energy_au"),
        "pipeline.final_peak_power_au": _metric_by_suffix(metrics, ".summary.peak_intensity_au"),
        "pipeline.final_bandwidth_rad_per_fs": _metric_by_suffix(
            metrics, ".summary.bandwidth_rad_per_fs"
        ),
    }


def _gnlse_available() -> bool:
    return importlib.util.find_spec("gnlse") is not None


def _build_stretcher_stage(*, length_m: float, beta2_ps2_per_m: float) -> FiberCfg | ToyFiberAmpCfg:
    if _gnlse_available():
        return FiberCfg(
            name="stretcher",
            physics=FiberPhysicsCfg(
                length_m=length_m,
                gamma_1_per_w_m=0.0,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[beta2_ps2_per_m]),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                grid_policy="force_pow2",
                z_saves=64,
            ),
        )

    return ToyFiberAmpCfg(
        name="stretcher",
        length_m=length_m,
        beta2_s2_per_m=beta2_ps2_per_m * 1e-24,
        gamma_w_inv_m=0.0,
        gain_db=0.0,
        loss_db_per_m=0.0,
        n_steps=20,
    )


def _build_shared_amp_stage() -> ToyFiberAmpCfg:
    return ToyFiberAmpCfg(**SHARED_AMP_KWARGS)


def _build_case_a_config(*, seed: int) -> PipelineConfig:
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=build_shared_laser_gen(),
        stages=[_build_shared_amp_stage()],
    )


def _build_case_b_config(*, seed: int) -> PipelineConfig:
    target_stretch_ratio = 20.0
    input_width_ps = 2.0
    stretcher_length_m = 100.0
    stretcher_beta2_s2_per_m = (
        np.sqrt(target_stretch_ratio**2 - 1.0)
        * (input_width_ps * 1e-12) ** 2
        / (4.0 * np.log(2.0) * stretcher_length_m)
    )
    stretcher_beta2_ps2_per_m = float(stretcher_beta2_s2_per_m * 1e24)

    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=build_shared_laser_gen(),
        stages=[
            _build_stretcher_stage(
                length_m=stretcher_length_m,
                beta2_ps2_per_m=stretcher_beta2_ps2_per_m,
            ),
            _build_shared_amp_stage(),
            TreacyGratingPairCfg(
                name="compressor",
                line_density_lpmm=600.0,
                incidence_angle_deg=20.0,
                separation_um=120_000.0,
                wavelength_nm=1560.0,
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
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    policy = {
        "cpa.emit_stage_plots": emit_plots,
        "cpa.stage_plot_dir": str(out_dir / "stage-plots"),
    }
    result = run_pipeline(cfg, policy=policy)
    payload = {
        "matching_criterion": "output_energy",
        "description": description,
        "comparison_metrics": _extract_comparison_metrics(result.metrics),
        "metrics": result.metrics,
        "artifacts": {**result.artifacts, **result.state.artifacts},
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

    case_a = _run_case(
        case_name="A_direct",
        description="Direct seed pulse into shared toy fiber amp.",
        cfg=_build_case_a_config(seed=seed),
        out_dir=out_dir / "case-a",
        emit_plots=emit_plots,
    )
    case_b = _run_case(
        case_name="B_cpa",
        description="CPA-style stretcher -> shared toy fiber amp -> Treacy compressor chain.",
        cfg=_build_case_b_config(seed=seed),
        out_dir=out_dir / "case-b",
        emit_plots=emit_plots,
    )

    comparison = {
        "seed": seed,
        "laser_gen": {
            "source": "toy_amp_shared.build_shared_laser_gen",
            "shared_spec": shared_laser_spec_summary(),
        },
        "shared_amp": SHARED_AMP_KWARGS,
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
