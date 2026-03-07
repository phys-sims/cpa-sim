from __future__ import annotations

import pytest

from cpa_sim.tuning.parameter_space import apply_parameter_values, set_dot_path

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
