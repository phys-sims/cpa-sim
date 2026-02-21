from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    TreacyGratingPairCfg,
)
from cpa_sim.pipeline import run_pipeline

DEFAULT_OUT_DIR = Path("artifacts/treacy-compressor-probe")


def _rms_width_fs(*, t_fs: np.ndarray, intensity: np.ndarray) -> float:
    weight = np.maximum(intensity, 0.0)
    norm = float(np.sum(weight))
    if norm <= 0.0:
        return 0.0
    t_mean = float(np.sum(t_fs * weight) / norm)
    variance = float(np.sum(((t_fs - t_mean) ** 2) * weight) / norm)
    return float(np.sqrt(max(variance, 0.0)))


def build_config(*, seed: int, separation_um: float, ci_safe: bool) -> PipelineConfig:
    if ci_safe:
        n_samples = 256
        time_window_fs = 2400.0
        fiber_length_m = 2.0
    else:
        n_samples = 1024
        time_window_fs = 6000.0
        fiber_length_m = 12.0

    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="gaussian",
                    amplitude=1.0,
                    width_fs=120.0,
                    center_wavelength_nm=1560.0,
                    n_samples=n_samples,
                    time_window_fs=time_window_fs,
                )
            )
        ),
        stages=[
            FiberCfg(
                name="fiber_regular_disp_1560nm",
                physics=FiberPhysicsCfg(
                    length_m=fiber_length_m,
                    loss_db_per_m=0.2,
                    gamma_1_per_w_m=0.0,
                    dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.022]),
                ),
            ),
            TreacyGratingPairCfg(
                name="treacy_compressor",
                line_density_lpmm=600.0,
                incidence_angle_deg=20.0,
                separation_um=separation_um,
                wavelength_nm=1560.0,
                n_passes=2,
                include_tod=True,
                apply_to_pulse=True,
            ),
        ],
    )


def run_probe(
    *,
    out_dir: Path,
    seed: int,
    ci_safe: bool,
    start_um: float,
    stop_um: float,
    step_um: float,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    separations = np.arange(start_um, stop_um + 0.5 * step_um, step_um)
    results: list[dict[str, float]] = []

    for separation_um in separations:
        cfg = build_config(seed=seed, separation_um=float(separation_um), ci_safe=ci_safe)
        result = run_pipeline(cfg)
        t_fs = np.asarray(result.state.pulse.grid.t)
        i_t = np.asarray(result.state.pulse.intensity_t)
        width_fs = _rms_width_fs(t_fs=t_fs, intensity=i_t)
        results.append(
            {
                "separation_um": float(separation_um),
                "rms_width_fs": width_fs,
                "peak_intensity_au": float(np.max(i_t)),
                "compressor_gdd_fs2": float(result.metrics["cpa.treacy_compressor.treacy_compressor.gdd_fs2"]),
                "compressor_tod_fs3": float(result.metrics["cpa.treacy_compressor.treacy_compressor.tod_fs3"]),
            }
        )

    best = min(results, key=lambda item: item["rms_width_fs"])
    payload = {
        "seed": seed,
        "ci_safe": ci_safe,
        "scan": {
            "start_um": start_um,
            "stop_um": stop_um,
            "step_um": step_um,
            "count": len(results),
        },
        "best": best,
        "results": results,
    }

    (out_dir / "probe_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (out_dir / "probe_results.csv").open("w", encoding="utf-8") as fh:
        fh.write("separation_um,rms_width_fs,peak_intensity_au,compressor_gdd_fs2,compressor_tod_fs3\n")
        for item in results:
            fh.write(
                f"{item['separation_um']:.1f},{item['rms_width_fs']:.6f},{item['peak_intensity_au']:.6f},"
                f"{item['compressor_gdd_fs2']:.6f},{item['compressor_tod_fs3']:.6f}\n"
            )

    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan Treacy separation to debug compressor behavior against regular-dispersion fiber chirp."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=1560)
    parser.add_argument("--ci-safe", action="store_true")
    parser.add_argument("--start-um", type=float, default=60_000.0)
    parser.add_argument("--stop-um", type=float, default=180_000.0)
    parser.add_argument("--step-um", type=float, default=5_000.0)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = run_probe(
        out_dir=args.out,
        seed=args.seed,
        ci_safe=args.ci_safe,
        start_um=args.start_um,
        stop_um=args.stop_um,
        step_um=args.step_um,
    )
    best = payload["best"]
    print(f"wrote summary: {args.out / 'probe_summary.json'}")
    print(
        "best separation: "
        f"{best['separation_um']:.1f} um "
        f"(rms_width_fs={best['rms_width_fs']:.4f}, peak_intensity_au={best['peak_intensity_au']:.4f})"
    )


if __name__ == "__main__":
    main()
