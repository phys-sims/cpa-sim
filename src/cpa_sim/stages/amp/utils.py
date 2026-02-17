from __future__ import annotations

import numpy as np


def field_gain_from_power_gain(gain_linear: float) -> float:
    """Convert intensity/power gain into an electric-field amplitude multiplier."""
    return float(np.sqrt(max(gain_linear, 0.0)))
