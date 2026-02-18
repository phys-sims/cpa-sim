from __future__ import annotations

import numpy as np


def normalized_cross_correlation(reference: np.ndarray, candidate: np.ndarray) -> float:
    """Return cosine similarity between two real-valued waveforms.

    Values are clamped to [0, 1] so callers can use ``1 - similarity`` as a bounded
    distortion metric.
    """

    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(candidate, dtype=float)
    if ref.shape != cur.shape:
        raise ValueError("reference and candidate must have the same shape")
    ref_norm = float(np.linalg.norm(ref))
    cur_norm = float(np.linalg.norm(cur))
    if ref_norm <= 0.0 or cur_norm <= 0.0:
        return 0.0
    score = float(np.dot(ref.ravel(), cur.ravel()) / (ref_norm * cur_norm))
    return float(np.clip(score, 0.0, 1.0))


def amplification_ratio(energy_out: float, energy_in: float) -> float:
    """Compute output/input energy ratio with safe handling for degenerate inputs."""

    if energy_in <= 0.0:
        return 0.0
    return float(energy_out / energy_in)
