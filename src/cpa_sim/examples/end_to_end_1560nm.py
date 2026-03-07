from __future__ import annotations

from pathlib import Path
from typing import Any

from cpa_sim.examples._shared import (
    ensure_out_dir,
    print_example_artifacts,
    run_example_with_default_policy,
    write_example_json,
)
from cpa_sim.models import (
    DispersionTaylorCfg,
    FiberAmpWrapCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RuntimeCfg,
    TreacyGratingPairCfg,
    WustGnlseNumericsCfg,
)

DEFAULT_OUT_DIR = Path("artifacts/end-to-end-1560nm")
DEFAULT_PLOT_DIR = DEFAULT_OUT_DIR / "stage-plots"
DEFAULT_SEED = 1560


def build_config(*, seed: int, ci_safe: bool) -> PipelineConfig:
    if ci_safe:
        n_samples = 256
        time_window_fs = 24000.0
        fiber_length_m = 2.0
    else:
        n_samples = 1024
        time_window_fs = 60000.0
        fiber_length_m = 50000

    laser_gen = LaserGenCfg(
        spec=LaserSpec(
            pulse=PulseSpec(
                shape="sech2",
                avg_power_w=0.1,
                rep_rate_mhz=1150,
                width_fs=7000.0,
                center_wavelength_nm=1560.0,
                n_samples=n_samples,
                time_window_fs=time_window_fs,
            )
        )
    )

    stages: list[Any] = [
        FiberCfg(
            name="fiber_regular_disp_1560nm",
            physics=FiberPhysicsCfg(
                length_m=fiber_length_m,
                loss_db_per_m=0.0,
                gamma_1_per_w_m=0.0,
                dispersion=DispersionTaylorCfg(
                    betas_psn_per_m=[0.022],
                ),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                z_saves=64 if ci_safe else 200,
                keep_full_solution=False,
            ),
        ),
        FiberAmpWrapCfg(
            name="fiber_amp_spm",
            power_out_w=5.0,
            physics=FiberPhysicsCfg(
                length_m=0.5 if ci_safe else 5.0,
                loss_db_per_m=0.2,
                gamma_1_per_w_m=0.01,
                dispersion=DispersionTaylorCfg(betas_psn_per_m=[0.0]),
            ),
            numerics=WustGnlseNumericsCfg(
                backend="wust_gnlse",
                z_saves=64 if ci_safe else 200,
                keep_full_solution=False,
            ),
        ),
        TreacyGratingPairCfg(
            name="treacy_compressor",
            line_density_lpmm=600.0,
            incidence_angle_deg=20.0,
            separation_um=120_000.0,
            wavelength_nm=1560.0,
            n_passes=2,
            include_tod=True,
            apply_to_pulse=True,
        ),
    ]

    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=laser_gen,
        stages=stages,
    )


def run_example(
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    plot_dir: Path = DEFAULT_PLOT_DIR,
    seed: int = DEFAULT_SEED,
    ci_safe: bool = False,
) -> dict[str, Any]:
    ensure_out_dir(out_dir)
    cfg = build_config(seed=seed, ci_safe=ci_safe)
    policy_overrides = {
        "cpa.emit_stage_plots": True,
        "cpa.plot.line.threshold_fraction": 1e-3,
        "cpa.plot.line.min_support_width": 0.0,
        "cpa.plot.line.pad_fraction": 0.05,
        "cpa.plot.heatmap.coverage_quantile": 0.999,
        "cpa.plot.heatmap.pad_fraction": 0.10,
        "cpa.plot.heatmap.fallback_behavior": "full_axis",
    }
    run_output = run_example_with_default_policy(
        cfg,
        stage_plot_dir=plot_dir,
        policy_overrides=policy_overrides,
    )
    result = run_output.result

    payload = {
        "seed": seed,
        "ci_safe": ci_safe,
        "policy": run_output.policy,
        "metrics": result.metrics,
        "observables": result.state.meta.get("observable_contract", {}),
        "artifacts": run_output.artifacts,
    }
    write_example_json(out_dir / "run_summary.json", payload)
    return payload


def main() -> None:
    output = run_example()
    print_example_artifacts(
        title="Generated end-to-end 1560nm artifacts:",
        artifacts={k: Path(v) for k, v in output["artifacts"].items()},
    )
    print(f"  summary_json: {DEFAULT_OUT_DIR / 'run_summary.json'}")
    print(f"artifacts emitted: {len(output['artifacts'])}")


if __name__ == "__main__":
    main()
