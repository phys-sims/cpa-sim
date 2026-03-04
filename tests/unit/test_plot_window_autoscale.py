from __future__ import annotations

import numpy as np

from cpa_sim.utils import _autoscale_window


def test_autoscale_window_focuses_on_signal_support() -> None:
    x = np.linspace(-100.0, 100.0, 1001)
    values = np.exp(-(x / 10.0) ** 2)

    lo, hi = _autoscale_window(x_axis=x, values=values, threshold_fraction=1e-2) or (None, None)

    assert lo is not None and hi is not None
    assert lo > -40.0
    assert hi < 40.0


def test_autoscale_window_falls_back_to_full_axis_for_flat_signal() -> None:
    x = np.linspace(-5.0, 5.0, 101)
    values = np.zeros_like(x)

    lo, hi = _autoscale_window(x_axis=x, values=values) or (None, None)

    assert lo == float(x.min())
    assert hi == float(x.max())
