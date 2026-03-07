from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from cpa_sim.models.state import LaserState

NormalizationMode = Literal["none", "peak", "area"]
TargetTraceKind = Literal["spectrum", "time_trace"]
TargetAxisKind = Literal["omega_offset_rad_per_fs", "wavelength_nm", "time_fs"]

_LIGHT_SPEED_NM_PER_FS = 299.792458


@dataclass(frozen=True)
class TargetTrace:
    axis: np.ndarray
    values: np.ndarray
    trace_kind: TargetTraceKind
    axis_kind: TargetAxisKind


def load_target_trace_csv(
    path: Path | str,
    *,
    x_column: str | int | None = None,
    y_column: str | int | None = None,
    trace_kind: TargetTraceKind = "spectrum",
    axis_kind: TargetAxisKind | None = None,
) -> TargetTrace:
    x, y = read_target_csv(path, x_column=x_column, y_column=y_column)
    resolved_axis_kind = axis_kind or _default_axis_kind(trace_kind)
    return TargetTrace(
        axis=np.asarray(x, dtype=float),
        values=np.asarray(y, dtype=float),
        trace_kind=trace_kind,
        axis_kind=resolved_axis_kind,
    )


def read_target_csv(
    path: Path | str,
    *,
    x_column: str | int | None = None,
    y_column: str | int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8") as fh:
        rows = [row for row in csv.reader(fh) if _keep_row(row)]

    if not rows:
        raise ValueError(f"Target CSV '{csv_path}' is empty.")

    has_header = _has_header_row(rows[0]) or isinstance(x_column, str) or isinstance(y_column, str)
    data_rows = rows[1:] if has_header else rows
    header = rows[0] if has_header else []

    x_idx = _resolve_column_index(
        x_column if x_column is not None else 0,
        row=header if has_header else rows[0],
        row_kind="header" if has_header else "data",
    )
    y_idx = _resolve_column_index(
        y_column if y_column is not None else 1,
        row=header if has_header else rows[0],
        row_kind="header" if has_header else "data",
    )

    if x_idx == y_idx:
        raise ValueError("Target CSV requires distinct x and y columns.")

    x_values: list[float] = []
    y_values: list[float] = []
    for row_idx, row in enumerate(data_rows, start=2 if has_header else 1):
        if max(x_idx, y_idx) >= len(row):
            raise ValueError(f"Target CSV row {row_idx} does not have columns {x_idx} and {y_idx}.")
        try:
            x_values.append(float(row[x_idx]))
            y_values.append(float(row[y_idx]))
        except ValueError as exc:
            raise ValueError(f"Target CSV row {row_idx} contains non-numeric values.") from exc

    if len(x_values) < 2:
        raise ValueError("Target CSV must contain at least two numeric samples.")

    axis = np.asarray(x_values, dtype=float)
    values = np.asarray(y_values, dtype=float)
    return axis, values


def normalize_trace(
    values: np.ndarray,
    *,
    axis: np.ndarray | None = None,
    mode: NormalizationMode = "none",
) -> np.ndarray:
    data = np.asarray(values, dtype=float)
    if data.ndim != 1:
        raise ValueError("Expected a 1D trace for normalization.")

    if mode == "none":
        return data

    weights = np.abs(data)
    if mode == "peak":
        denom = float(np.max(weights))
    elif mode == "area":
        if axis is None:
            denom = float(np.sum(weights))
        else:
            x = np.asarray(axis, dtype=float)
            if x.shape != data.shape:
                raise ValueError(
                    "axis and values must have identical shapes for area normalization."
                )
            denom = abs(float(np.trapezoid(weights, x=x)))
    else:
        raise ValueError(f"Unsupported normalization mode '{mode}'.")

    if denom <= 0.0:
        raise ValueError("Cannot normalize a zero-valued trace.")
    return data / denom


def select_roi(
    axis: np.ndarray,
    values: np.ndarray,
    *,
    window: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(axis, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.shape != y.shape:
        raise ValueError("axis and values must have identical shapes.")

    if window is None:
        return x, y

    low, high = window
    if low >= high:
        raise ValueError("ROI window must satisfy low < high.")

    mask = (x >= low) & (x <= high)
    if not np.any(mask):
        raise ValueError("ROI window excludes all samples.")
    return x[mask], y[mask]


def interpolate_trace(
    source_axis: np.ndarray,
    source_values: np.ndarray,
    target_axis: np.ndarray,
    *,
    fill_value: float = 0.0,
) -> np.ndarray:
    x_src = np.asarray(source_axis, dtype=float)
    y_src = np.asarray(source_values, dtype=float)
    x_tgt = np.asarray(target_axis, dtype=float)
    if x_src.shape != y_src.shape:
        raise ValueError("source_axis and source_values must have identical shapes.")

    sorted_axis, sorted_values = _sort_and_average_duplicates(x_src, y_src)
    if sorted_axis.size < 2:
        raise ValueError("Interpolation requires at least two unique source axis samples.")

    return np.interp(x_tgt, sorted_axis, sorted_values, left=fill_value, right=fill_value)


def simulator_trace_for_alignment(
    state: LaserState,
    *,
    trace_kind: TargetTraceKind,
    axis_kind: TargetAxisKind,
) -> tuple[np.ndarray, np.ndarray]:
    if trace_kind == "time_trace":
        if axis_kind != "time_fs":
            raise ValueError("time_trace objectives only support axis_kind='time_fs'.")
        return (
            np.asarray(state.pulse.grid.t, dtype=float),
            np.asarray(state.pulse.intensity_t, dtype=float),
        )

    if axis_kind == "time_fs":
        raise ValueError("spectrum objectives cannot use axis_kind='time_fs'.")

    spectrum = np.asarray(state.pulse.spectrum_w, dtype=float)
    omega_offset = np.asarray(state.pulse.grid.w, dtype=float)
    if axis_kind == "omega_offset_rad_per_fs":
        return omega_offset, spectrum
    if axis_kind == "wavelength_nm":
        wavelength = offset_omega_to_wavelength_nm(
            omega_offset,
            center_wavelength_nm=state.pulse.grid.center_wavelength_nm,
        )
        return wavelength, spectrum
    raise ValueError(f"Unsupported axis_kind '{axis_kind}'.")


def wavelength_nm_to_offset_omega(
    wavelength_nm: np.ndarray,
    *,
    center_wavelength_nm: float,
) -> np.ndarray:
    wavelength = np.asarray(wavelength_nm, dtype=float)
    if np.any(wavelength <= 0.0):
        raise ValueError("wavelength values must be > 0.")
    omega_abs = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / wavelength
    omega0 = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / float(center_wavelength_nm)
    return omega_abs - omega0


def offset_omega_to_wavelength_nm(
    omega_offset_rad_per_fs: np.ndarray,
    *,
    center_wavelength_nm: float,
) -> np.ndarray:
    omega_offset = np.asarray(omega_offset_rad_per_fs, dtype=float)
    omega0 = 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / float(center_wavelength_nm)
    omega_abs = omega0 + omega_offset
    if np.any(omega_abs <= 0.0):
        raise ValueError("offset omega maps to non-physical absolute omega <= 0.")
    return 2.0 * np.pi * _LIGHT_SPEED_NM_PER_FS / omega_abs


def _keep_row(row: list[str]) -> bool:
    if not row:
        return False
    stripped = [item.strip() for item in row]
    if not any(stripped):
        return False
    first = stripped[0]
    if first.startswith("#"):
        return False
    return True


def _has_header_row(row: list[str]) -> bool:
    # Heuristic: if either of the first two columns is non-numeric, treat as a header row.
    head = [item.strip() for item in row[:2]]
    if len(head) < 2:
        return False
    return not (_is_float(head[0]) and _is_float(head[1]))


def _resolve_column_index(
    selector: str | int,
    *,
    row: list[str],
    row_kind: Literal["header", "data"],
) -> int:
    if isinstance(selector, int):
        if selector < 0:
            raise ValueError("CSV column indices must be non-negative.")
        if selector >= len(row):
            raise ValueError(f"CSV {row_kind} does not include column index {selector}.")
        return selector

    if row_kind != "header":
        raise ValueError("Named CSV columns require a header row.")

    normalized = [item.strip() for item in row]
    try:
        return normalized.index(selector)
    except ValueError as exc:
        raise ValueError(f"CSV header does not include column '{selector}'.") from exc


def _sort_and_average_duplicates(
    axis: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(axis)
    sorted_axis = axis[order]
    sorted_values = values[order]

    unique_axis, inverse = np.unique(sorted_axis, return_inverse=True)
    if unique_axis.size == sorted_axis.size:
        return sorted_axis, sorted_values

    averaged = np.zeros(unique_axis.size, dtype=float)
    counts = np.zeros(unique_axis.size, dtype=float)
    for idx, value in zip(inverse, sorted_values):
        averaged[idx] += float(value)
        counts[idx] += 1.0
    averaged /= counts
    return unique_axis, averaged


def _default_axis_kind(trace_kind: TargetTraceKind) -> TargetAxisKind:
    if trace_kind == "time_trace":
        return "time_fs"
    return "omega_offset_rad_per_fs"


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
