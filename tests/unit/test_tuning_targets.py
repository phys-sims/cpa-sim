from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cpa_sim.tuning.targets import (
    interpolate_trace,
    normalize_trace,
    read_target_csv,
    select_roi,
    wavelength_nm_to_offset_omega,
)

pytestmark = pytest.mark.unit


def test_read_target_csv_with_header_and_named_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "target.csv"
    csv_path.write_text(
        "wavelength_nm,intensity\n1030,0.1\n1031,0.2\n1032,0.5\n",
        encoding="utf-8",
    )

    x, y = read_target_csv(csv_path, x_column="wavelength_nm", y_column="intensity")

    assert np.allclose(x, [1030.0, 1031.0, 1032.0])
    assert np.allclose(y, [0.1, 0.2, 0.5])


def test_normalize_trace_peak_and_area_modes() -> None:
    values = np.asarray([0.0, 1.0, 2.0], dtype=float)
    peak = normalize_trace(values, mode="peak")

    assert np.allclose(peak, [0.0, 0.5, 1.0])

    axis = np.asarray([0.0, 1.0, 2.0], dtype=float)
    area = normalize_trace(values, axis=axis, mode="area")
    assert np.isclose(np.trapz(np.abs(area), x=axis), 1.0)

    # Descending axes should still normalize by positive area magnitude.
    axis_desc = axis[::-1]
    values_desc = values[::-1]
    area_desc = normalize_trace(values_desc, axis=axis_desc, mode="area")
    assert np.isclose(abs(np.trapz(np.abs(area_desc), x=axis_desc)), 1.0)


def test_normalize_trace_rejects_zero_trace_for_peak_or_area() -> None:
    zeros = np.zeros(4, dtype=float)

    with pytest.raises(ValueError, match="zero-valued"):
        normalize_trace(zeros, mode="peak")

    with pytest.raises(ValueError, match="zero-valued"):
        normalize_trace(zeros, mode="area")


def test_interpolate_trace_sorts_and_averages_duplicate_source_axis() -> None:
    source_axis = np.asarray([1.0, 0.0, 1.0, 2.0], dtype=float)
    source_values = np.asarray([2.0, 0.0, 4.0, 2.0], dtype=float)
    target_axis = np.asarray([0.0, 0.5, 1.0, 1.5, 2.0], dtype=float)

    interpolated = interpolate_trace(source_axis, source_values, target_axis)

    # duplicate x=1 values are averaged to 3.0 before interpolation
    assert np.allclose(interpolated, [0.0, 1.5, 3.0, 2.5, 2.0])


def test_select_roi_window_and_empty_selection_errors() -> None:
    axis = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0], dtype=float)
    values = np.asarray([0.0, 1.0, 2.0, 1.0, 0.0], dtype=float)

    x_roi, y_roi = select_roi(axis, values, window=(-1.0, 1.0))

    assert np.allclose(x_roi, [-1.0, 0.0, 1.0])
    assert np.allclose(y_roi, [1.0, 2.0, 1.0])

    with pytest.raises(ValueError, match="excludes all"):
        select_roi(axis, values, window=(3.0, 4.0))


def test_wavelength_to_offset_omega_relative_to_center() -> None:
    center_wavelength = 1030.0
    wavelength = np.asarray([1030.0, 1020.0, 1040.0], dtype=float)

    omega_offset = wavelength_nm_to_offset_omega(
        wavelength,
        center_wavelength_nm=center_wavelength,
    )

    assert np.isclose(omega_offset[0], 0.0)
    assert omega_offset[1] > 0.0
    assert omega_offset[2] < 0.0
