from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from cpa_sim.models import (
    DispersionInterpolationCfg,
    DispersionTaylorCfg,
    FiberCfg,
    FiberPhysicsCfg,
    LaserGenCfg,
    LaserSpec,
    PipelineConfig,
    PulseSpec,
    RamanCfg,
    RuntimeCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.plotting import plot_dispersive_wave_maps_from_npz
from cpa_sim.plotting.common import load_pyplot
from cpa_sim.plotting.dispersive_wave import (
    _load_npz_traces,
    _prepare_wust_map_data,
    _render_wust_delay_map,
    _render_wust_wavelength_map,
)
from cpa_sim.reporting import run_pipeline_with_plot_policy, write_json

DEFAULT_OUT_DIR = Path("out")
DEFAULT_PRESET = "dispersion"
DEFAULT_CASE = "both"
DEFAULT_STAGE_NAME = "fiber_dispersive_wave"
_TAYLOR_STAGE_NAME = "fiber_dispersive_wave_taylor"
_INTERP_STAGE_NAME = "fiber_dispersive_wave_interpolation"
_TIME_RANGE_PS = (-0.5, 5.0)
_WL_RANGE_NM = (400.0, 1400.0)
_NEFF_TABLE_PATH = Path(__file__).with_name("data") / "neff_pcf_dat01.csv"
_UPSTREAM_TAYLOR_BETAS_PSN_PER_M = [
    -0.024948815481502,
    8.875391917212998e-05,
    -9.247462376518329e-08,
    1.508210856829677e-10,
]

PresetName = Literal["dispersion"]
CaseName = Literal["taylor", "interpolation"]
CaseSelection = Literal["taylor", "interpolation", "both"]


@dataclass(frozen=True)
class ShowcaseCaseDefinition:
    preset: PresetName
    case: CaseName
    stage_name: str
    cfg: PipelineConfig
    center_wavelength_nm: float
    time_range_ps: tuple[float, float]
    wl_range_nm: tuple[float, float]


def _interpolation_dispersion_cfg() -> DispersionInterpolationCfg:
    lambdas_nm: list[float] = []
    effective_indices: list[float] = []

    # Upstream provenance: extracted once from WUST-FOG gnlse `data/neff_pcf.mat`
    # using `dat[:, 0]` and `dat[:, 1]` from `examples/test_dispersion.py`.
    with _NEFF_TABLE_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            if first.startswith("#") or first == "wavelength_nm":
                continue
            lambdas_nm.append(float(first))
            effective_indices.append(float(row[1]))

    if len(lambdas_nm) < 2:
        raise ValueError(
            f"Expected at least two interpolation samples in {_NEFF_TABLE_PATH}; "
            f"got {len(lambdas_nm)}."
        )

    return DispersionInterpolationCfg(
        effective_indices=effective_indices,
        lambdas_nm=lambdas_nm,
        central_wavelength_nm=835.0,
    )


def _build_dispersion_cfg(
    *,
    seed: int,
    stage_name: str,
    dispersion: DispersionTaylorCfg | DispersionInterpolationCfg,
) -> PipelineConfig:
    return PipelineConfig(
        runtime=RuntimeCfg(seed=seed),
        laser_gen=LaserGenCfg(
            spec=LaserSpec(
                pulse=PulseSpec(
                    shape="sech2",
                    peak_power_w=10000.0,
                    width_fs=50.0,
                    center_wavelength_nm=835.0,
                    n_samples=16384,
                    time_window_fs=12500.0,
                )
            )
        ),
        stages=[
            FiberCfg(
                name=stage_name,
                physics=FiberPhysicsCfg(
                    length_m=0.15,
                    loss_db_per_m=0.0,
                    gamma_1_per_w_m=0.0,
                    dispersion=dispersion,
                    raman=RamanCfg(model="blowwood"),
                    self_steepening=True,
                ),
                numerics=WustGnlseNumericsCfg(
                    backend="wust_gnlse",
                    z_saves=200,
                    keep_full_solution=True,
                ),
            )
        ],
    )


def _resolve_case_selection(case: CaseSelection) -> tuple[CaseName, ...]:
    if case == "taylor":
        return ("taylor",)
    if case == "interpolation":
        return ("interpolation",)
    if case == "both":
        return ("taylor", "interpolation")
    raise ValueError(f"Unsupported case selection: {case!r}")


def _build_dispersion_case(*, case: CaseName, seed: int) -> ShowcaseCaseDefinition:
    dispersion: DispersionTaylorCfg | DispersionInterpolationCfg
    if case == "taylor":
        stage_name = _TAYLOR_STAGE_NAME
        dispersion = DispersionTaylorCfg(
            betas_psn_per_m=list(_UPSTREAM_TAYLOR_BETAS_PSN_PER_M),
        )
    else:
        stage_name = _INTERP_STAGE_NAME
        dispersion = _interpolation_dispersion_cfg()

    return ShowcaseCaseDefinition(
        preset="dispersion",
        case=case,
        stage_name=stage_name,
        cfg=_build_dispersion_cfg(seed=seed, stage_name=stage_name, dispersion=dispersion),
        center_wavelength_nm=835.0,
        time_range_ps=_TIME_RANGE_PS,
        wl_range_nm=_WL_RANGE_NM,
    )


def build_showcase_case_definitions(
    *,
    preset: PresetName = "dispersion",
    case: CaseSelection = "both",
    seed: int = 7,
) -> list[ShowcaseCaseDefinition]:
    if preset != "dispersion":
        raise ValueError(f"Unsupported showcase preset: {preset!r}")
    return [
        _build_dispersion_case(case=case_name, seed=seed)
        for case_name in _resolve_case_selection(case)
    ]


def _plot_combined_comparison(
    *,
    taylor_npz: Path,
    interpolation_npz: Path,
    out_path: Path,
    center_wavelength_nm: float,
    time_range_ps: tuple[float, float],
    wl_range_nm: tuple[float, float],
) -> Path:
    taylor_z_m, taylor_t_fs, taylor_w_rad_per_fs, taylor_at_zt, taylor_aw_zw = _load_npz_traces(
        npz_path=taylor_npz
    )
    interp_z_m, interp_t_fs, interp_w_rad_per_fs, interp_at_zt, interp_aw_zw = _load_npz_traces(
        npz_path=interpolation_npz
    )
    taylor_data = _prepare_wust_map_data(
        at_zt=taylor_at_zt,
        z_m=taylor_z_m,
        t_fs=taylor_t_fs,
        w_rad_per_fs=taylor_w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        aw_zw=taylor_aw_zw,
        time_range_ps=time_range_ps,
        wl_range_nm=wl_range_nm,
    )
    interpolation_data = _prepare_wust_map_data(
        at_zt=interp_at_zt,
        z_m=interp_z_m,
        t_fs=interp_t_fs,
        w_rad_per_fs=interp_w_rad_per_fs,
        center_wavelength_nm=center_wavelength_nm,
        aw_zw=interp_aw_zw,
        time_range_ps=time_range_ps,
        wl_range_nm=wl_range_nm,
    )

    plt = load_pyplot()
    fig, axes = plt.subplots(2, 2, figsize=(15, 7))
    _render_wust_wavelength_map(ax=axes[0, 0], map_data=taylor_data, scale="linear")
    _render_wust_wavelength_map(ax=axes[0, 1], map_data=interpolation_data, scale="linear")
    _render_wust_delay_map(ax=axes[1, 0], map_data=taylor_data, scale="linear")
    _render_wust_delay_map(ax=axes[1, 1], map_data=interpolation_data, scale="linear")

    axes[0, 0].set_title("Results for Taylor expansion")
    axes[0, 1].set_title("Results for interpolation")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    return out_path


def run_showcase(
    *,
    out_dir: Path,
    preset: PresetName = "dispersion",
    case: CaseSelection = "both",
    seed: int = 7,
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_plot_dir = out_dir / "stage_plots"
    case_definitions = build_showcase_case_definitions(preset=preset, case=case, seed=seed)

    artifacts: dict[str, str] = {}
    metrics_by_case: dict[str, dict[str, object]] = {}
    npz_by_case: dict[CaseName, Path] = {}

    for case_def in case_definitions:
        run_output = run_pipeline_with_plot_policy(case_def.cfg, stage_plot_dir=stage_plot_dir)
        artifacts.update(run_output.artifacts)
        metrics_by_case[case_def.case] = run_output.metrics_payload

        npz_path = Path(run_output.artifacts[f"{case_def.stage_name}.z_traces_npz"])
        npz_by_case[case_def.case] = npz_path

        stage_plots = plot_dispersive_wave_maps_from_npz(
            npz_path=npz_path,
            center_wavelength_nm=case_def.center_wavelength_nm,
            out_dir=stage_plot_dir,
            stem=case_def.stage_name,
            compat_mode="wust",
            time_range_ps=case_def.time_range_ps,
            wl_range_nm=case_def.wl_range_nm,
        )
        artifacts[f"{case_def.stage_name}.plot_wavelength_vs_distance_linear"] = str(
            stage_plots.wavelength_linear
        )
        artifacts[f"{case_def.stage_name}.plot_wavelength_vs_distance_log"] = str(
            stage_plots.wavelength_log
        )
        artifacts[f"{case_def.stage_name}.plot_delay_vs_distance_linear"] = str(
            stage_plots.delay_linear
        )
        artifacts[f"{case_def.stage_name}.plot_delay_vs_distance_log"] = str(stage_plots.delay_log)

    if "taylor" in npz_by_case and "interpolation" in npz_by_case:
        combined_path = _plot_combined_comparison(
            taylor_npz=npz_by_case["taylor"],
            interpolation_npz=npz_by_case["interpolation"],
            out_path=stage_plot_dir / f"{DEFAULT_STAGE_NAME}_comparison_wust.png",
            center_wavelength_nm=835.0,
            time_range_ps=_TIME_RANGE_PS,
            wl_range_nm=_WL_RANGE_NM,
        )
        artifacts[f"{DEFAULT_STAGE_NAME}.plot_comparison_wust"] = str(combined_path)

    write_json(
        out_dir / "metrics.json",
        {
            "schema_version": "cpa.metrics.v1",
            "preset": preset,
            "case_selection": case,
            "cases": metrics_by_case,
        },
    )
    write_json(
        out_dir / "artifacts.json",
        {
            "schema_version": "cpa.artifacts.v1",
            "preset": preset,
            "case_selection": case,
            "paths": artifacts,
        },
    )

    return artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate gnlse dispersive-wave showcase plots.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--preset", choices=[DEFAULT_PRESET], default=DEFAULT_PRESET)
    parser.add_argument(
        "--case",
        choices=["taylor", "interpolation", "both"],
        default=DEFAULT_CASE,
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    artifacts = run_showcase(
        out_dir=args.out,
        preset=cast(PresetName, args.preset),
        case=cast(CaseSelection, args.case),
        seed=args.seed,
    )
    for key in sorted(artifacts):
        if key.endswith(".z_traces_npz") or ".plot_" in key:
            print(f"{key}: {artifacts[key]}")


if __name__ == "__main__":
    main()
