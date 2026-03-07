from __future__ import annotations

import sys
import types

import pytest

from cpa_sim.tuning.parameter_space import (
    apply_parameter_values,
    set_dot_path,
    tuning_to_parameter_space,
)
from cpa_sim.tuning.schema import TuneConfig

pytestmark = pytest.mark.unit

pytestmark = pytest.mark.unit


def test_set_dot_path_updates_existing_leaf() -> None:
    payload = {"fiber": {"physics": {"length_m": 1.0}}}

    patched = set_dot_path(payload, "fiber.physics.length_m", 2.5)

    assert patched["fiber"]["physics"]["length_m"] == 2.5


def test_set_dot_path_rejects_unknown_segment() -> None:
    payload = {"fiber": {"physics": {"length_m": 1.0}}}

    with pytest.raises(ValueError, match="Unknown path segment 'fiberr'"):
        set_dot_path(payload, "fiberr.physics.length_m", 2.5)


def test_set_dot_path_rejects_unknown_leaf_by_default() -> None:
    payload = {"fiber": {"physics": {"length_m": 1.0}}}

    with pytest.raises(ValueError, match="Unknown target key 'length_mm'"):
        set_dot_path(payload, "fiber.physics.length_mm", 2.5)


def test_set_dot_path_can_create_missing_when_requested() -> None:
    payload = {"fiber": {"physics": {}}}

    patched = set_dot_path(payload, "fiber.physics.length_m", 2.5, create_missing=True)

    assert patched["fiber"]["physics"]["length_m"] == 2.5


def test_apply_parameter_values_rejects_unknown_path() -> None:
    payload = {"fiber": {"physics": {"length_m": 1.0}}}

    with pytest.raises(ValueError, match="Unknown path segment 'fiberr'"):
        apply_parameter_values(payload, {"fiberr.physics.length_m": 3.0})


def test_tuning_to_parameter_space_uses_dot_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ml = types.ModuleType("phys_sims_utils.ml")

    class Parameter:
        def __init__(
            self, name: str, path: str, lower: float, upper: float, transform: str | None = None
        ):
            self.name = name
            self.path = path
            self.lower = lower
            self.upper = upper
            self.transform = transform

    class ParameterSpace:
        def __init__(self, parameters: list[Parameter]):
            self.parameters = parameters

    fake_ml.Parameter = Parameter
    fake_ml.ParameterSpace = ParameterSpace

    monkeypatch.setitem(sys.modules, "phys_sims_utils", types.ModuleType("phys_sims_utils"))
    monkeypatch.setitem(sys.modules, "phys_sims_utils.ml", fake_ml)

    config = TuneConfig.model_validate(
        {
            "base_pipeline_config": {"runtime": {"seed": 0}},
            "parameters": [
                {
                    "name": "comp_sep",
                    "path": "compressor.separation_um",
                    "bounds": [100000.0, 300000.0],
                }
            ],
            "objective": {"metric": "cpa.metrics.summary.fwhm_fs", "direction": "minimize"},
        }
    )

    space = tuning_to_parameter_space(config)

    assert len(space.parameters) == 1
    assert space.parameters[0].path == "compressor.separation_um"
