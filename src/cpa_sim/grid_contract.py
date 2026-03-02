from __future__ import annotations

import numpy as np


def assert_offset_omega_grid(w: np.ndarray, *, atol: float = 1e-9) -> None:
    """Assert that a spectral axis is an offset angular-frequency grid (Δω).

    The contract for :class:`PulseGrid` is that ``w`` represents centered frequency
    offsets in ``rad/fs`` (typically from ``fftshift(2π*fftfreq(...))``), not absolute
    optical angular frequency.
    """

    arr = np.asarray(w, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"Offset angular-frequency grid must be 1-D, got shape={arr.shape}.")
    if arr.size < 2:
        raise ValueError("Offset angular-frequency grid must contain at least two samples.")

    diffs = np.diff(arr)
    if not np.all(diffs > 0.0):
        raise ValueError("Offset angular-frequency grid must be strictly increasing.")

    step = float(diffs[0])
    if not np.allclose(diffs, step, rtol=0.0, atol=atol):
        spacing_err = float(np.max(np.abs(diffs - step)))
        raise ValueError(
            "Offset angular-frequency grid must have uniform FFT bin spacing: "
            f"max|diff(w)-dw|={spacing_err:.6e}, atol={atol:.6e}."
        )

    mean_bound = 0.5 * abs(step) + atol

    mean_w = float(np.mean(arr))
    if abs(mean_w) >= mean_bound:
        raise ValueError(
            "PulseGrid.w must be a Δω grid centered near 0 rad/fs: "
            f"mean(w)={mean_w:.6e}, allowed<=0.5*dw+atol={mean_bound:.6e}."
        )

    symmetry_target = -arr[::-1]
    if arr.size % 2 == 0:
        # Even-length fftshift grids are half-bin centered around 0.
        symmetry_target = symmetry_target - step

    symmetry_err = float(np.max(np.abs(arr - symmetry_target)))
    if symmetry_err >= atol:
        raise ValueError(
            "PulseGrid.w must be approximately antisymmetric for shifted FFT grids: "
            f"max|w + reverse(w)|={symmetry_err:.6e}, atol={atol:.6e}."
        )
