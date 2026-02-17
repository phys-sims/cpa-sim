from __future__ import annotations

import math

import numpy as np


def assert_uniform_spacing(values: np.ndarray, *, rtol: float = 1e-6, atol: float = 1e-12) -> None:
    if values.size < 2:
        return
    diffs = np.diff(values)
    if not np.allclose(diffs, diffs[0], rtol=rtol, atol=atol):
        raise ValueError("Fiber stage requires a uniformly spaced pulse time grid.")


def nearest_power_of_two(size: int) -> int:
    if size < 1:
        raise ValueError("Grid size must be >= 1")
    return 1 << int(round(math.log2(size)))


def has_large_prime_factor(size: int, *, limit: int = 13) -> bool:
    n = size
    factor = 2
    largest = 1
    while factor * factor <= n:
        while n % factor == 0:
            largest = factor
            n //= factor
        factor += 1
    if n > 1:
        largest = max(largest, n)
    return largest > limit


def resample_complex_uniform(signal: np.ndarray, old_t: np.ndarray, new_size: int) -> np.ndarray:
    new_t = np.linspace(float(old_t[0]), float(old_t[-1]), new_size)
    real = np.interp(new_t, old_t, np.real(signal))
    imag = np.interp(new_t, old_t, np.imag(signal))
    return real + 1j * imag
