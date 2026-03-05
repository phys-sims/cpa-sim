from __future__ import annotations

import numpy as np

from cpa_sim.plotting.common import auto_xlim_from_intensity


def test_auto_xlim_from_intensity_focuses_signal_region() -> None:
    x = np.linspace(-6000.0, 6000.0, 4096)
    z = np.linspace(0.0, 1.0, 80)
    center = 200.0
    sigma = 80.0

    pulse_t = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    z_mod = 0.8 + 0.2 * np.sin(2.0 * np.pi * z)
    i2d = z_mod[:, None] * pulse_t[None, :]

    xmin, xmax = auto_xlim_from_intensity(x, i2d, coverage=0.999, pad_frac=0.10)

    assert xmax > xmin
    assert xmin < center < xmax
    assert (xmax - xmin) < 0.2 * (x.max() - x.min())


def test_auto_xlim_from_intensity_handles_zero_or_nan_maps() -> None:
    x = np.linspace(-6000.0, 6000.0, 1024)

    zeros = np.zeros((10, x.size))
    xlim_zero = auto_xlim_from_intensity(x, zeros)
    assert xlim_zero == (float(x.min()), float(x.max()))

    nans = np.full((10, x.size), np.nan)
    xlim_nan = auto_xlim_from_intensity(x, nans)
    assert xlim_nan == (float(x.min()), float(x.max()))


def test_auto_xlim_from_intensity_handles_unsorted_x() -> None:
    x = np.array([3.0, -1.0, 2.0, 0.0, 1.0])
    i2d = np.array([[0.0, 0.0, 1.0, 4.0, 1.0], [0.0, 0.0, 0.5, 2.0, 0.5]])

    xmin, xmax = auto_xlim_from_intensity(x, i2d, coverage=0.8, pad_frac=0.0)

    assert xmin <= 0.0 <= xmax
