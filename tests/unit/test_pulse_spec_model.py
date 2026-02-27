from __future__ import annotations

import pytest
from pydantic import ValidationError

from cpa_sim.models.state import PulseSpec


@pytest.mark.unit
@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"avg_power_w": 1.0, "peak_power_w": 2.0},
            "Exactly one pulse normalization input may be explicitly set",
        ),
        (
            {"amplitude": 1.0, "avg_power_w": 1.0},
            "PulseSpec.amplitude cannot be set together",
        ),
    ],
)
def test_pulse_spec_rejects_conflicting_power_normalization_inputs(
    kwargs: dict[str, float],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        PulseSpec(**kwargs)


@pytest.mark.unit
def test_pulse_spec_rejects_conflicting_width_inputs() -> None:
    with pytest.raises(ValidationError, match="Only one pulse width input may be explicitly set"):
        PulseSpec(width_fs=120.0, intensity_autocorr_fwhm_fs=180.0)


@pytest.mark.unit
def test_pulse_spec_warns_when_amplitude_is_explicitly_set() -> None:
    with pytest.warns(DeprecationWarning, match=r"PulseSpec\.amplitude is deprecated"):
        PulseSpec(amplitude=2.0)


@pytest.mark.unit
def test_pulse_spec_schema_marks_amplitude_deprecated_and_exposes_new_fields() -> None:
    schema = PulseSpec.model_json_schema()
    properties = schema["properties"]

    assert properties["amplitude"]["deprecated"] is True
    assert "avg_power_w" in properties
    assert "pulse_energy_j" in properties
    assert "peak_power_w" in properties
    assert "intensity_autocorr_fwhm_fs" in properties
