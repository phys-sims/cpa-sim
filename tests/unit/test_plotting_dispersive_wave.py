from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cpa_sim.models import HeatmapNormPolicy, PlotWindowPolicy
from cpa_sim.plotting import build_default_plot_paths, plot_dispersive_wave_maps_from_npz
from cpa_sim.plotting.common import resolve_heatmap_render_params
from cpa_sim.plotting.dispersive_wave import (
    _interpolate_to_uniform_wavelength_grid,
    _load_npz_traces,
    _normalize_by_max,
    _prepare_wust_map_data,
    _to_db_floor,
)


@pytest.mark.unit
def test_build_default_plot_paths_uses_expected_naming(tmp_path: Path) -> None:
    paths = build_default_plot_paths(out_dir=tmp_path, stem="fiber_demo")

    assert paths.delay_linear.name == "fiber_demo_delay_vs_distance_linear.png"
    assert paths.delay_log.name == "fiber_demo_delay_vs_distance_log.png"
    assert paths.wavelength_linear.name == "fiber_demo_wavelength_vs_distance_linear.png"
    assert paths.wavelength_log.name == "fiber_demo_wavelength_vs_distance_log.png"


@pytest.mark.unit
def test_plot_dispersive_wave_maps_from_npz_generates_all_outputs(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")

    n_z = 4
    n_t = 16
    z_m = np.linspace(0.0, 0.15, n_z)
    t_fs = np.linspace(-100.0, 100.0, n_t)
    at_zt = np.ones((n_z, n_t), dtype=np.complex128)

    npz_path = tmp_path / "z_traces.npz"
    np.savez_compressed(
        npz_path,
        z_m=z_m,
        t_fs=t_fs,
        at_zt_real=at_zt.real,
        at_zt_imag=at_zt.imag,
    )

    paths = plot_dispersive_wave_maps_from_npz(
        npz_path=npz_path,
        center_wavelength_nm=835.0,
        out_dir=tmp_path / "plots",
        stem="fiber_demo",
    )

    for path in (
        paths.delay_linear,
        paths.delay_log,
        paths.wavelength_linear,
        paths.wavelength_log,
    ):
        assert path.exists()
        assert path.stat().st_size > 0


@pytest.mark.unit
def test_plot_dispersive_wave_maps_from_npz_wust_generates_all_outputs(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")

    n_z = 4
    n_t = 16
    z_m = np.linspace(0.0, 0.15, n_z)
    t_fs = np.linspace(-100.0, 100.0, n_t)
    at_zt = np.ones((n_z, n_t), dtype=np.complex128)

    npz_path = tmp_path / "z_traces_wust.npz"
    np.savez_compressed(
        npz_path,
        z_m=z_m,
        t_fs=t_fs,
        at_zt_real=at_zt.real,
        at_zt_imag=at_zt.imag,
    )

    paths = plot_dispersive_wave_maps_from_npz(
        npz_path=npz_path,
        center_wavelength_nm=835.0,
        out_dir=tmp_path / "plots_wust",
        stem="fiber_demo",
        compat_mode="wust",
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )

    for path in (
        paths.delay_linear,
        paths.delay_log,
        paths.wavelength_linear,
        paths.wavelength_log,
    ):
        assert path.exists()
        assert path.stat().st_size > 0


@pytest.mark.unit
def test_log_dynamic_range_norm_anchors_to_peak_for_hdr_maps() -> None:
    pytest.importorskip("matplotlib")

    values = np.array(
        [
            [1e-12, 1e-8, 1e-4],
            [1e-2, 1.0, 10.0],
        ],
        dtype=float,
    )
    policy = PlotWindowPolicy(heatmap_norm=HeatmapNormPolicy(scale="log", dynamic_range_db=30.0))

    render = resolve_heatmap_render_params(values=values, scale=None, policy=policy)

    assert render.norm is not None
    assert render.vmax == pytest.approx(10.0)
    assert render.vmin == pytest.approx(0.01)
    assert np.nanmin(render.values) >= render.vmin
    assert np.nanmax(render.values) <= render.vmax


@pytest.mark.unit
def test_linear_powerlaw_norm_uses_percentile_window_and_gamma() -> None:
    values = np.array([[0.0, 1.0, 5.0, 100.0]], dtype=float)
    policy = PlotWindowPolicy(
        heatmap_norm=HeatmapNormPolicy(
            scale="linear",
            vmin_percentile=25.0,
            vmax_percentile=75.0,
            gamma=0.5,
        )
    )

    render = resolve_heatmap_render_params(values=values, scale=None, policy=policy)

    assert render.norm is None
    assert render.vmin == pytest.approx(0.75)
    assert render.vmax == pytest.approx(28.75)
    assert np.nanmax(render.values) == pytest.approx(render.vmax)
    assert np.nanmin(render.values) == pytest.approx(render.vmin)
    assert render.values[0, 2] > 5.0


@pytest.mark.unit
def test_wust_delay_axis_converts_fs_to_ps() -> None:
    at_zt = np.ones((2, 3), dtype=np.complex128)
    z_m = np.array([0.0, 0.1], dtype=float)
    t_fs = np.array([-500.0, 0.0, 1000.0], dtype=float)
    w_rad_per_fs = np.array([-0.2, 0.0, 0.2], dtype=float)

    map_data = _prepare_wust_map_data(
        at_zt=at_zt,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=835.0,
        aw_zw=None,
        time_range_ps=(-0.5, 1.0),
        wl_range_nm=(400.0, 1400.0),
    )

    assert np.allclose(map_data.delay_ps, np.array([-0.5, 0.0, 1.0]))


@pytest.mark.unit
def test_wust_map_respects_requested_time_and_wavelength_ranges() -> None:
    at_zt = np.ones((3, 16), dtype=np.complex128)
    z_m = np.array([0.0, 0.075, 0.15], dtype=float)
    t_fs = np.linspace(-1000.0, 2000.0, 16)
    w_rad_per_fs = np.linspace(-0.5, 0.5, 16)

    map_data = _prepare_wust_map_data(
        at_zt=at_zt,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=835.0,
        aw_zw=None,
        time_range_ps=(-1.0, 2.0),
        wl_range_nm=(450.0, 1300.0),
    )

    assert map_data.time_range_ps == (-1.0, 2.0)
    assert map_data.wl_range_nm == (450.0, 1300.0)
    assert float(np.min(map_data.wavelength_nm)) >= 450.0
    assert float(np.max(map_data.wavelength_nm)) <= 1300.0


@pytest.mark.unit
def test_wust_linear_map_normalizes_by_domain_max() -> None:
    values = np.array([[1.0, 2.0], [4.0, 0.0]], dtype=float)
    normalized = _normalize_by_max(values)

    assert np.max(normalized) == pytest.approx(1.0)
    assert normalized[0, 0] == pytest.approx(0.25)
    assert normalized[0, 1] == pytest.approx(0.5)
    assert normalized[1, 0] == pytest.approx(1.0)


@pytest.mark.unit
def test_wust_db_conversion_clamps_to_negative_40_db() -> None:
    values = np.array([1.0, 1e-3, 0.0], dtype=float)
    values_db = _to_db_floor(values)

    assert values_db[0] == pytest.approx(0.0)
    assert values_db[1] == pytest.approx(-30.0)
    assert values_db[2] == pytest.approx(-40.0)


@pytest.mark.unit
def test_wust_wavelength_axis_is_sorted_ascending() -> None:
    n_t = 16
    at_zt = np.ones((2, n_t), dtype=np.complex128)
    z_m = np.array([0.0, 0.1], dtype=float)
    t_fs = np.linspace(-100.0, 100.0, n_t)
    w_rad_per_fs = np.linspace(-0.4, 0.4, n_t)

    map_data = _prepare_wust_map_data(
        at_zt=at_zt,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        center_wavelength_nm=835.0,
        aw_zw=None,
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )

    assert np.all(np.diff(map_data.wavelength_nm) > 0.0)


@pytest.mark.unit
def test_wust_interpolates_to_uniform_wavelength_grid() -> None:
    wavelength_nm = np.array([400.0, 700.0, 1400.0], dtype=float)
    values = np.array([[0.0, 1.0, 0.0]], dtype=float)

    wl_uniform, interpolated = _interpolate_to_uniform_wavelength_grid(
        wavelength_nm=wavelength_nm,
        values=values,
    )

    spacing = np.diff(wl_uniform)
    assert np.allclose(spacing, spacing[0])
    assert interpolated.shape == values.shape
    assert interpolated[0, 1] == pytest.approx(np.interp(wl_uniform[1], wavelength_nm, values[0]))


@pytest.mark.unit
def test_wust_npz_loading_prefers_saved_aw_when_present(tmp_path: Path) -> None:
    z_m = np.array([0.0, 0.1], dtype=float)
    t_fs = np.linspace(-100.0, 100.0, 8)
    at_zt = np.array(
        [
            [
                1.0 + 0.0j,
                0.5 + 0.2j,
                0.3 + 0.0j,
                0.1 + 0.0j,
                0.0 + 0.0j,
                0.1 + 0.0j,
                0.2 + 0.0j,
                0.3 + 0.0j,
            ],
            [
                0.8 + 0.0j,
                0.4 + 0.1j,
                0.2 + 0.0j,
                0.1 + 0.0j,
                0.0 + 0.0j,
                0.1 + 0.0j,
                0.1 + 0.0j,
                0.2 + 0.0j,
            ],
        ],
        dtype=np.complex128,
    )
    aw_saved = np.zeros_like(at_zt)
    aw_saved[:, 3] = 10.0 + 0.0j
    w_rad_per_fs = np.linspace(-0.4, 0.4, 8)

    npz_path = tmp_path / "with_aw.npz"
    np.savez_compressed(
        npz_path,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        at_zt_real=at_zt.real,
        at_zt_imag=at_zt.imag,
        aw_zw_real=aw_saved.real,
        aw_zw_imag=aw_saved.imag,
    )

    loaded_z, loaded_t, loaded_w, loaded_at, loaded_aw = _load_npz_traces(npz_path=npz_path)
    map_saved = _prepare_wust_map_data(
        at_zt=loaded_at,
        z_m=loaded_z,
        t_fs=loaded_t,
        w_rad_per_fs=loaded_w,
        center_wavelength_nm=835.0,
        aw_zw=loaded_aw,
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )
    map_fft = _prepare_wust_map_data(
        at_zt=loaded_at,
        z_m=loaded_z,
        t_fs=loaded_t,
        w_rad_per_fs=loaded_w,
        center_wavelength_nm=835.0,
        aw_zw=None,
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )

    assert map_saved.aw_source == "saved_aw"
    assert not np.allclose(map_saved.wavelength_linear, map_fft.wavelength_linear)


@pytest.mark.unit
def test_wust_npz_loading_falls_back_to_fft_when_aw_missing(tmp_path: Path) -> None:
    z_m = np.array([0.0, 0.1], dtype=float)
    t_fs = np.linspace(-100.0, 100.0, 8)
    at_zt = np.array(
        [
            [
                1.0 + 0.0j,
                0.5 + 0.2j,
                0.3 + 0.0j,
                0.1 + 0.0j,
                0.0 + 0.0j,
                0.1 + 0.0j,
                0.2 + 0.0j,
                0.3 + 0.0j,
            ],
            [
                0.8 + 0.0j,
                0.4 + 0.1j,
                0.2 + 0.0j,
                0.1 + 0.0j,
                0.0 + 0.0j,
                0.1 + 0.0j,
                0.1 + 0.0j,
                0.2 + 0.0j,
            ],
        ],
        dtype=np.complex128,
    )
    w_rad_per_fs = np.linspace(-0.4, 0.4, 8)

    npz_path = tmp_path / "without_aw.npz"
    np.savez_compressed(
        npz_path,
        z_m=z_m,
        t_fs=t_fs,
        w_rad_per_fs=w_rad_per_fs,
        at_zt_real=at_zt.real,
        at_zt_imag=at_zt.imag,
    )

    loaded_z, loaded_t, loaded_w, loaded_at, loaded_aw = _load_npz_traces(npz_path=npz_path)
    map_data = _prepare_wust_map_data(
        at_zt=loaded_at,
        z_m=loaded_z,
        t_fs=loaded_t,
        w_rad_per_fs=loaded_w,
        center_wavelength_nm=835.0,
        aw_zw=loaded_aw,
        time_range_ps=(-0.5, 5.0),
        wl_range_nm=(400.0, 1400.0),
    )

    assert loaded_aw is None
    assert map_data.aw_source == "fft_at"
