from __future__ import annotations

from pathlib import Path

import numpy as np

from cpa_sim.plotting import build_default_plot_paths, plot_dispersive_wave_maps_from_npz


def test_build_default_plot_paths_uses_expected_naming(tmp_path: Path) -> None:
    paths = build_default_plot_paths(out_dir=tmp_path, stem="fiber_demo")

    assert paths.delay_linear.name == "fiber_demo_delay_vs_distance_linear.png"
    assert paths.delay_log.name == "fiber_demo_delay_vs_distance_log.png"
    assert paths.wavelength_linear.name == "fiber_demo_wavelength_vs_distance_linear.png"
    assert paths.wavelength_log.name == "fiber_demo_wavelength_vs_distance_log.png"


def test_plot_dispersive_wave_maps_from_npz_generates_all_outputs(tmp_path: Path) -> None:
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
