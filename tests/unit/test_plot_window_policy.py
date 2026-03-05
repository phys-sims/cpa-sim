from __future__ import annotations

import numpy as np

from cpa_sim.models import HeatmapWindowPolicy, LineWindowPolicy, PlotWindowPolicy
from cpa_sim.plotting.common import auto_xlim_from_intensity, autoscale_window_1d


def test_line_window_policy_stabilizes_narrow_peak_width() -> None:
    x = np.linspace(-1000.0, 1000.0, 4001)
    y = np.exp(-0.5 * (x / 2.0) ** 2)

    xlim = autoscale_window_1d(
        x_axis=x,
        values=y,
        policy=LineWindowPolicy(
            threshold_fraction=0.4,
            min_support_width=120.0,
            pad_fraction=0.1,
        ),
    )

    assert xlim is not None
    lo, hi = xlim
    assert hi - lo >= 132.0
    assert lo < 0.0 < hi


def test_heatmap_policy_handles_broad_chirped_profile() -> None:
    x = np.linspace(-8000.0, 8000.0, 4096)
    z = np.linspace(0.0, 1.0, 64)
    sigma = np.linspace(800.0, 2500.0, z.size)[:, None]
    i2d = np.exp(-0.5 * (x[None, :] / sigma) ** 2)

    lo, hi = auto_xlim_from_intensity(
        x,
        i2d,
        policy=HeatmapWindowPolicy(coverage_quantile=0.995, pad_fraction=0.05),
    )

    assert lo < 0.0 < hi
    assert (hi - lo) < (x.max() - x.min())
    assert (hi - lo) > 3000.0


def test_line_window_policy_covers_multimodal_profile_support() -> None:
    x = np.linspace(-200.0, 200.0, 2001)
    y = np.exp(-0.5 * ((x + 80.0) / 10.0) ** 2) + 0.9 * np.exp(-0.5 * ((x - 60.0) / 12.0) ** 2)

    lo, hi = autoscale_window_1d(
        x_axis=x,
        values=y,
        policy=PlotWindowPolicy(
            line=LineWindowPolicy(threshold_fraction=0.2, min_support_width=0.0, pad_fraction=0.05)
        ),
    ) or (None, None)

    assert lo is not None and hi is not None
    assert lo < -75.0
    assert hi > 55.0


def test_heatmap_policy_rejects_low_snr_tails_with_quantile() -> None:
    rng = np.random.default_rng(123)
    x = np.linspace(-5000.0, 5000.0, 4096)
    z = np.linspace(0.0, 1.0, 80)
    signal = np.exp(-0.5 * (x / 130.0) ** 2)
    noise = np.abs(rng.normal(loc=0.0, scale=2e-3, size=(z.size, x.size)))
    i2d = 0.2 * signal[None, :] + noise

    lo, hi = auto_xlim_from_intensity(
        x,
        i2d,
        policy=PlotWindowPolicy(
            heatmap=HeatmapWindowPolicy(coverage_quantile=0.90, pad_fraction=0.05)
        ),
    )

    assert lo < 0.0 < hi
    assert (hi - lo) < 4500.0
