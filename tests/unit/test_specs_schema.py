from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from specs.schema import (
    FiberSpecRecord,
    GratingSpecRecord,
    load_catalog,
    load_spec,
)


@pytest.mark.unit
def test_missing_required_fields_fail_with_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "missing_id.yml"
    path.write_text("type: fiber\nspecs: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError) as exc:
        load_spec(path)

    assert "id" in str(exc.value)


@pytest.mark.unit
def test_fiber_unit_conversions() -> None:
    record = load_spec("specs/catalog/fiber/fiber_thorlabs_pmdcf.yml")
    assert isinstance(record, FiberSpecRecord)

    assert record.normalized["effective_area_m2"]["value_m2"] == pytest.approx(20e-12)
    assert record.normalized["loss_db_per_m"]["value_db_per_m"] == pytest.approx(0.0004)
    assert record.normalized["dispersion_ps_per_nm_km"]["value_s_per_m2"] == pytest.approx(-1e-4)


@pytest.mark.unit
def test_grating_line_density_conversion() -> None:
    record = load_spec("specs/catalog/grating/grating_wasatch_wp_600_1550_50p8.yml")
    assert isinstance(record, GratingSpecRecord)

    assert record.normalized["line_density"]["value_lines_per_m"] == pytest.approx(600_000.0)


@pytest.mark.unit
def test_nonlinear_requirements_fail_fast() -> None:
    payload = {
        "id": "demo_fiber",
        "type": "fiber",
        "vendor": {"manufacturer": "demo"},
        "specs": {
            "dispersion": {"reference_wavelength_nm": 1550},
            "optical": {"effective_area_um2": {"value": 20}},
        },
    }
    record = FiberSpecRecord.model_validate(payload)

    with pytest.raises(ValidationError) as exc:
        record.require_nonlinear_inputs()

    assert "missing nonlinear inputs" in str(exc.value)


@pytest.mark.unit
def test_fiber_contradictory_gamma_rejected() -> None:
    payload = {
        "id": "bad_fiber",
        "type": "fiber",
        "vendor": {"manufacturer": "demo"},
        "specs": {
            "dispersion": {"reference_wavelength_nm": 1550},
            "optical": {"effective_area_um2": {"value": 80}},
            "nonlinear": {"n2_m2_per_w": 2.6e-20, "gamma_1_per_w_m": 100.0},
        },
    }

    with pytest.raises(ValidationError) as exc:
        FiberSpecRecord.model_validate(payload)

    assert "contradictory" in str(exc.value)


@pytest.mark.unit
def test_golden_parse_existing_catalog_files() -> None:
    catalog = load_catalog()
    assert set(catalog) == {
        "thorlabs_pmdcf_1550",
        "wasatch_wp_600lmm_1550_vph_50p8",
        "calmar_coronado_benchtop_edfa_1550",
        "pritel_uoc_1550_ultrafast_optical_clock",
    }
