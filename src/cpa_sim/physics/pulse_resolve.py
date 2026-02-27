from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

_GAUSSIAN_AUTOCORR_DECONV_FACTOR = math.sqrt(2.0)
# Commonly cited as dividing by 1.543; equivalent multiplier is approximately 0.648.
_SECH2_AUTOCORR_WIDTH_MULTIPLIER = 0.648
_SHAPE_TO_AUTOCORR_DECONV = {
    "gaussian": _GAUSSIAN_AUTOCORR_DECONV_FACTOR,
    "sech2": 1.0 / _SECH2_AUTOCORR_WIDTH_MULTIPLIER,
}


@runtime_checkable
class PulseSpecLike(Protocol):
    """Subset of pulse-spec fields used by pulse normalization helpers."""

    shape: str
    width_fs: float
    intensity_autocorr_fwhm_fs: float | None
    pulse_energy_j: float | None
    avg_power_w: float | None
    peak_power_w: float | None
    rep_rate_mhz: float
    amplitude: float


def rep_rate_hz(rep_rate_mhz: float) -> float:
    """Convert repetition rate from MHz to Hz."""

    return float(rep_rate_mhz) * 1e6


def _field_explicitly_set(spec: object, field_name: str) -> bool:
    fields_set = getattr(spec, "model_fields_set", None)
    return isinstance(fields_set, set) and field_name in fields_set


def resolve_intensity_fwhm_fs(pulse_spec: PulseSpecLike) -> float:
    """Resolve pulse intensity FWHM in femtoseconds from width or autocorrelation inputs."""

    autocorr_fs = pulse_spec.intensity_autocorr_fwhm_fs
    width_is_explicit = _field_explicitly_set(pulse_spec, "width_fs")
    if autocorr_fs is not None and not width_is_explicit:
        try:
            deconvolution_factor = _SHAPE_TO_AUTOCORR_DECONV[pulse_spec.shape]
        except KeyError as exc:
            raise ValueError(
                "Unknown pulse shape for autocorrelation deconvolution: "
                f"{pulse_spec.shape!r}. Expected one of: gaussian, sech2."
            ) from exc
        return float(autocorr_fs) / deconvolution_factor

    return float(pulse_spec.width_fs)


def resolve_pulse_energy_j(pulse_spec: PulseSpecLike) -> float | None:
    """Resolve energy-per-pulse in joules from direct energy or average-power inputs."""

    if pulse_spec.pulse_energy_j is not None:
        return float(pulse_spec.pulse_energy_j)

    if pulse_spec.avg_power_w is not None:
        return float(pulse_spec.avg_power_w) / rep_rate_hz(pulse_spec.rep_rate_mhz)

    return None


def peak_power_w_from_energy_j(energy_j: float, width_fs: float, shape: str) -> float:
    """Compute peak power from pulse energy using intensity-profile analytic integrals."""

    width_s = float(width_fs) * 1e-15
    if width_s <= 0.0:
        raise ValueError("width_fs must be > 0 to compute peak power.")

    if shape == "gaussian":
        return float(energy_j) * (2.0 * math.sqrt(math.log(2.0))) / (width_s * math.sqrt(math.pi))

    if shape == "sech2":
        return float(energy_j) * math.acosh(math.sqrt(2.0)) / width_s

    raise ValueError(f"Unknown pulse shape for peak-power conversion: {shape!r}.")


def resolve_peak_power_w(pulse_spec: PulseSpecLike, width_fs: float) -> float:
    """Resolve peak power in watts with deterministic precedence across pulse inputs."""

    if pulse_spec.peak_power_w is not None:
        return float(pulse_spec.peak_power_w)

    energy_j = resolve_pulse_energy_j(pulse_spec)
    if energy_j is not None:
        return peak_power_w_from_energy_j(energy_j=energy_j, width_fs=width_fs, shape=pulse_spec.shape)

    amplitude_is_explicit = _field_explicitly_set(pulse_spec, "amplitude")
    if amplitude_is_explicit:
        return float(pulse_spec.amplitude) ** 2

    if hasattr(pulse_spec, "amplitude") and float(pulse_spec.amplitude) == 1.0:
        return 1.0

    raise ValueError(
        "Peak power could not be resolved. Provide peak_power_w, pulse_energy_j, avg_power_w, "
        "or explicitly set amplitude (legacy)."
    )
