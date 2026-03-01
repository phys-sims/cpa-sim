from __future__ import annotations

import math
import warnings
from importlib import import_module, metadata
from typing import Any

import numpy as np

from cpa_sim.models.config import (
    DispersionInterpolationCfg,
    DispersionTaylorCfg,
    FiberPhysicsCfg,
    WustGnlseNumericsCfg,
)
from cpa_sim.models.state import LaserState
from cpa_sim.phys_pipeline_compat import StageResult
from cpa_sim.stages.fiber.utils.grid import (
    has_large_prime_factor,
    nearest_power_of_two,
    resample_complex_uniform,
)
from cpa_sim.stages.fiber.utils.units import fs_to_ps

_LIGHT_SPEED_M_PER_S = 299792458.0
_FS_TO_S = 1e-15


def _ensure_numpy_math_compat() -> None:
    # gnlse currently references np.math; NumPy 2 removed that alias.
    if not hasattr(np, "math"):
        np.math = math  # type: ignore[attr-defined]


def _import_gnlse() -> Any:
    try:
        return import_module("gnlse")
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError(
            "Fiber backend 'wust_gnlse' requires the optional 'gnlse' package. "
            "Install with: pip install -e '.[gnlse]'"
        ) from exc


def _resolve_gamma(physics: FiberPhysicsCfg, *, center_wavelength_nm: float) -> float:
    if physics.gamma_1_per_w_m is not None:
        return physics.gamma_1_per_w_m
    if physics.n2_m2_per_w is None or physics.aeff_m2 is None:
        raise ValueError(
            "Fiber physics must provide gamma_1_per_w_m or both n2_m2_per_w and aeff_m2."
        )
    wavelength_m = center_wavelength_nm * 1e-9
    omega0 = 2.0 * np.pi * _LIGHT_SPEED_M_PER_S / wavelength_m
    return float(physics.n2_m2_per_w * omega0 / (_LIGHT_SPEED_M_PER_S * physics.aeff_m2))


def _build_dispersion(gnlse: Any, physics: FiberPhysicsCfg) -> Any:
    if isinstance(physics.dispersion, DispersionTaylorCfg):
        return gnlse.DispersionFiberFromTaylor(
            physics.loss_db_per_m,
            physics.dispersion.betas_psn_per_m,
        )
    if isinstance(physics.dispersion, DispersionInterpolationCfg):
        return gnlse.DispersionFiberFromInterpolation(
            physics.loss_db_per_m,
            np.asarray(physics.dispersion.effective_indices, dtype=float),
            np.asarray(physics.dispersion.lambdas_nm, dtype=float),
            physics.dispersion.central_wavelength_nm,
        )
    raise TypeError("Unsupported dispersion config.")


def _build_raman_model(gnlse: Any, physics: FiberPhysicsCfg) -> Any | None:
    if physics.raman is None:
        return None
    model_name = f"raman_{physics.raman.model}"
    if not hasattr(gnlse, model_name):
        raise ValueError(f"Requested Raman model is not available in gnlse: {physics.raman.model}")
    return getattr(gnlse, model_name)


def _apply_grid_policy(
    state: LaserState,
    *,
    numerics: WustGnlseNumericsCfg,
    stage_name: str,
) -> tuple[LaserState, dict[str, str]]:
    out = state.deepcopy()
    old_t = np.asarray(out.pulse.grid.t, dtype=float)
    field_t = out.pulse.field_t
    n_points = field_t.size
    artifacts: dict[str, str] = {}

    if numerics.grid_policy == "force_pow2":
        n_points = nearest_power_of_two(n_points)
    elif numerics.grid_policy == "force_resolution":
        if numerics.resolution_override is None:
            raise ValueError("resolution_override is required when grid_policy='force_resolution'.")
        n_points = numerics.resolution_override

    if has_large_prime_factor(n_points):
        warnings.warn(
            "WUST gnlse often performs better with FFT sizes that avoid large prime factors.",
            stacklevel=2,
        )
        artifacts[f"{stage_name}.grid_large_prime_factor"] = "true"

    if n_points != field_t.size:
        new_t = np.linspace(float(old_t[0]), float(old_t[-1]), n_points)
        out.pulse.field_t = resample_complex_uniform(field_t, old_t, n_points)
        new_dt = float(new_t[1] - new_t[0]) if n_points > 1 else out.pulse.grid.dt
        new_w = np.fft.fftshift(2.0 * np.pi * np.fft.fftfreq(n_points, d=new_dt))
        new_dw = float(new_w[1] - new_w[0]) if n_points > 1 else out.pulse.grid.dw
        out.pulse.grid = out.pulse.grid.model_copy(
            update={
                "t": new_t.tolist(),
                "dt": new_dt,
                "w": new_w.tolist(),
                "dw": new_dw,
            }
        )
        artifacts[f"{stage_name}.resampled_points"] = str(n_points)

    return out, artifacts


def run_wust_gnlse(
    state: LaserState,
    *,
    stage_name: str,
    physics: FiberPhysicsCfg,
    numerics: WustGnlseNumericsCfg,
) -> StageResult[LaserState]:
    _ensure_numpy_math_compat()
    gnlse = _import_gnlse()
    out, artifacts = _apply_grid_policy(state, numerics=numerics, stage_name=stage_name)

    t_fs = np.asarray(out.pulse.grid.t, dtype=float)
    time_window_ps = (
        numerics.time_window_override_ps
        if numerics.time_window_override_ps is not None
        else fs_to_ps(float(t_fs[-1] - t_fs[0]))
    )

    setup = gnlse.GNLSESetup()
    setup.resolution = out.pulse.field_t.size
    setup.time_window = float(time_window_ps)
    setup.wavelength = out.pulse.grid.center_wavelength_nm
    setup.fiber_length = physics.length_m
    setup.nonlinearity = _resolve_gamma(
        physics,
        center_wavelength_nm=out.pulse.grid.center_wavelength_nm,
    )
    setup.pulse_model = np.asarray(out.pulse.field_t, dtype=np.complex128)
    setup.z_saves = numerics.z_saves
    setup.self_steepening = physics.self_steepening
    setup.dispersion_model = _build_dispersion(gnlse, physics)
    raman_model = _build_raman_model(gnlse, physics)
    if raman_model is not None:
        setup.raman_model = raman_model
    if hasattr(setup, "method"):
        setup.method = numerics.method
    if hasattr(setup, "rtol"):
        setup.rtol = numerics.rtol
    if hasattr(setup, "atol"):
        setup.atol = numerics.atol

    solver = gnlse.GNLSE(setup)
    solution = solver.run()

    at = np.asarray(solution.At)
    final_at = np.asarray(at[-1], dtype=np.complex128) if at.ndim > 1 else at.astype(np.complex128)
    out.pulse.field_t = final_at
    out.pulse.intensity_t = np.abs(final_at) ** 2

    recomputed_aw = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(final_at)))
    out.pulse.field_w = recomputed_aw
    out.pulse.spectrum_w = np.abs(recomputed_aw) ** 2

    out.meta.setdefault("pulse", {})
    out.meta["pulse"].update({"field_units": "sqrt(W)", "power_is_absA2_W": True})

    artifacts[f"{stage_name}.backend"] = "wust_gnlse"
    artifacts[f"{stage_name}.time_window_ps"] = f"{time_window_ps:.12g}"
    artifacts[f"{stage_name}.resolution"] = str(setup.resolution)
    if numerics.keep_full_solution:
        artifacts[f"{stage_name}.solution_saved"] = "z_traces_in_memory"
    if numerics.record_backend_version:
        try:
            artifacts[f"{stage_name}.backend_version"] = metadata.version("gnlse")
        except metadata.PackageNotFoundError:  # pragma: no cover
            artifacts[f"{stage_name}.backend_version"] = "unknown"
    out.artifacts.update(artifacts)

    power_in_w = np.abs(np.asarray(state.pulse.field_t)) ** 2
    power_out_w = np.abs(out.pulse.field_t) ** 2
    dt_in_fs = float(state.pulse.grid.dt)
    dt_out_fs = float(out.pulse.grid.dt)

    energy_in_au = float(np.sum(power_in_w) * dt_in_fs)
    energy_out_au = float(np.sum(power_out_w) * dt_out_fs)
    energy_in_j = float(np.sum(power_in_w) * dt_in_fs * _FS_TO_S)
    energy_out_j = float(np.sum(power_out_w) * dt_out_fs * _FS_TO_S)
    spectral_rms = float(np.sqrt(np.mean(np.abs(out.pulse.field_w) ** 2)))
    metrics = {
        f"{stage_name}.energy_in_au": energy_in_au,
        f"{stage_name}.energy_out_au": energy_out_au,
        f"{stage_name}.energy_in_j": energy_in_j,
        f"{stage_name}.energy_out_j": energy_out_j,
        f"{stage_name}.energy_ratio": energy_out_au / energy_in_au
        if energy_in_au > 0.0
        else float("nan"),
        f"{stage_name}.grid_points": float(out.pulse.field_t.size),
        f"{stage_name}.spectral_rms_au": spectral_rms,
    }
    out.metrics.update(metrics)
    return StageResult(state=out, metrics=metrics)
