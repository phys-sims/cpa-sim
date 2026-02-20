from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _nested_get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def lines_per_mm_to_lines_per_m(value: float) -> float:
    return value * 1_000.0


def um2_to_m2(value: float) -> float:
    return value * 1e-12


def db_per_km_to_db_per_m(value: float) -> float:
    return value / 1_000.0


def ps_per_nm_km_to_s_per_m2(value: float) -> float:
    return value * 1e-6


def fs2_per_m_to_s2_per_m(value: float) -> float:
    return value * 1e-30


def _compute_fiber_gamma(n2_m2_per_w: float, a_eff_m2: float, wavelength_m: float) -> float:
    # gamma = n2 * omega0 / (c * Aeff) == 2*pi*n2 / (lambda*Aeff)
    return (2.0 * 3.141592653589793 * n2_m2_per_w) / (wavelength_m * a_eff_m2)


class CatalogRecordBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    vendor: dict[str, Any] = Field(default_factory=dict)


class FiberSpecRecord(CatalogRecordBase):
    model_config = ConfigDict(extra="allow")

    type: Literal["fiber"]
    specs: dict[str, Any] = Field(default_factory=dict)

    normalized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_normalized(self) -> FiberSpecRecord:
        normalized: dict[str, Any] = {}

        dispersion_ps_nm_km = _to_float(
            _nested_get(self.specs, "dispersion", "dispersion_ps_per_nm_km", "value")
        )
        if dispersion_ps_nm_km is not None:
            normalized["dispersion_ps_per_nm_km"] = {
                "raw": dispersion_ps_nm_km,
                "raw_unit": "ps/(nm·km)",
                "value_s_per_m2": ps_per_nm_km_to_s_per_m2(dispersion_ps_nm_km),
            }

        loss_db_km = _to_float(_nested_get(self.specs, "optical", "attenuation_db_per_km", "typical"))
        if loss_db_km is not None:
            normalized["loss_db_per_m"] = {
                "raw": loss_db_km,
                "raw_unit": "dB/km",
                "value_db_per_m": db_per_km_to_db_per_m(loss_db_km),
            }

        a_eff_um2 = _to_float(_nested_get(self.specs, "optical", "effective_area_um2", "value"))
        a_eff_m2: float | None = None
        if a_eff_um2 is not None:
            a_eff_m2 = um2_to_m2(a_eff_um2)
            normalized["effective_area_m2"] = {
                "raw": a_eff_um2,
                "raw_unit": "um^2",
                "value_m2": a_eff_m2,
            }

        fs2_per_m = _to_float(
            _nested_get(self.specs, "dispersion", "group_velocity_dispersion_fs2_per_m", "value")
        )
        if fs2_per_m is not None:
            normalized["gvd_s2_per_m"] = {
                "raw": fs2_per_m,
                "raw_unit": "fs^2/m",
                "value_s2_per_m": fs2_per_m_to_s2_per_m(fs2_per_m),
            }

        gamma = _to_float(_nested_get(self.specs, "nonlinear", "gamma_1_per_w_m"))
        n2 = _to_float(_nested_get(self.specs, "nonlinear", "n2_m2_per_w"))
        ref_lambda_nm = _to_float(_nested_get(self.specs, "dispersion", "reference_wavelength_nm"))
        computed_gamma: float | None = None

        if n2 is not None and a_eff_m2 is not None and ref_lambda_nm is not None:
            computed_gamma = _compute_fiber_gamma(n2_m2_per_w=n2, a_eff_m2=a_eff_m2, wavelength_m=ref_lambda_nm * 1e-9)
            normalized["gamma_1_per_w_m"] = {
                "source": "computed",
                "value_1_per_w_m": computed_gamma,
                "inputs": {
                    "n2_m2_per_w": n2,
                    "a_eff_m2": a_eff_m2,
                    "reference_wavelength_nm": ref_lambda_nm,
                },
            }

        if gamma is not None:
            normalized["gamma_explicit_1_per_w_m"] = {
                "source": "explicit",
                "value_1_per_w_m": gamma,
            }
            if computed_gamma is not None:
                mismatch = abs(gamma - computed_gamma) / max(abs(computed_gamma), 1e-30)
                if mismatch > 0.05:
                    raise ValueError(
                        "Fiber nonlinear parameters are contradictory: explicit gamma_1_per_w_m "
                        "is inconsistent with n2_m2_per_w, effective_area_um2, and reference_wavelength_nm."
                    )

        self.normalized = normalized
        return self

    def require_nonlinear_inputs(self) -> float:
        explicit = _to_float(_nested_get(self.specs, "nonlinear", "gamma_1_per_w_m"))
        if explicit is not None:
            return explicit

        computed = _nested_get(self.normalized, "gamma_1_per_w_m", "value_1_per_w_m")
        if isinstance(computed, (int, float)):
            return float(computed)

        raise ValidationError.from_exception_data(
            title="FiberSpecRecord",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": ("specs", "nonlinear"),
                    "msg": (
                        "Nonlinear adapter inputs require gamma_1_per_w_m, or all of n2_m2_per_w, "
                        "effective_area_um2.value, and dispersion.reference_wavelength_nm to compute gamma."
                    ),
                    "input": self.specs.get("nonlinear"),
                    "ctx": {"error": "missing nonlinear inputs"},
                }
            ],
        )


class GratingSpecRecord(CatalogRecordBase):
    model_config = ConfigDict(extra="allow")

    type: Literal["grating"]
    specs: dict[str, Any] = Field(default_factory=dict)
    normalized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_normalized(self) -> GratingSpecRecord:
        lines_per_mm = _to_float(_nested_get(self.specs, "spatial_frequency_lines_per_mm", "value"))
        if lines_per_mm is not None:
            self.normalized = {
                "line_density": {
                    "raw": lines_per_mm,
                    "raw_unit": "lines/mm",
                    "value_lines_per_m": lines_per_mm_to_lines_per_m(lines_per_mm),
                }
            }
        return self


class AmpSpecRecord(CatalogRecordBase):
    model_config = ConfigDict(extra="allow")

    type: Literal["amp", "edfa"]
    specs: dict[str, Any] = Field(default_factory=dict)


class LaserSpecRecord(CatalogRecordBase):
    model_config = ConfigDict(extra="allow")

    type: Literal["laser"]
    specs: dict[str, Any] = Field(default_factory=dict)


CatalogSpecRecord = Annotated[
    FiberSpecRecord | GratingSpecRecord | AmpSpecRecord | LaserSpecRecord,
    Field(discriminator="type"),
]


def load_spec(path: str | Path) -> CatalogSpecRecord:
    spec_path = Path(path)
    with spec_path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    adapter = TypeAdapter(CatalogSpecRecord)
    return adapter.validate_python(payload)


def load_catalog(root: str | Path = "specs/catalog", *, as_dict: bool = True) -> dict[str, CatalogSpecRecord] | list[CatalogSpecRecord]:
    root_path = Path(root)
    records: list[CatalogSpecRecord] = []
    for yml_path in sorted(root_path.glob("*/*.yml")):
        records.append(load_spec(yml_path))

    if as_dict:
        return {record.id: record for record in records}
    return records
