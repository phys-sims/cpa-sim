# FreeSpaceStage: Treacy grating‑pair compressor backend (reference)

> **Stability:** This file is intended to be **rarely edited**. It defines the physics, unit conventions, config schema, and acceptance criteria for a Treacy grating‑pair free-space backend in `cpa-sim`.

---

## 1) Scope and goal

Implement a `FreeSpaceStage` backend that models a **Treacy grating‑pair compressor** as a **phase‑only** element:

1. Computes **GDD** and **TOD** from grating geometry at a chosen center wavelength.
2. Optionally applies the resulting spectral phase to the pulse spectrum.
3. Matches the **LaserCalculator** “Grating pair dispersion calculator” for identical inputs (double‑pass Treacy).

### Out of scope (v1)
- spatial chirp / beam walkoff / finite apertures
- grating efficiency / polarization / substrate material dispersion
- higher orders > TOD
- Martinez stretcher geometry (future backend)

---

## 2) Contract dependencies (must comply)

### Unit/FFT/sign conventions
Follow `ADR-0001-conventions-units.md` (internal authority):
- internal units: `fs`, `um`, `rad`
- angular frequency: `rad/fs`
- speed of light: `c = 0.299792458 um/fs`
- metrics must use explicit unit suffixes (e.g., `gdd_fs2`, `omega0_rad_per_fs`).

### Execution substrate
Follow `ADR-0005-phys-pipeline-contract-adoption.md`:
- `StageConfig`, `StageResult`, pipeline primitives come from `phys-pipeline`
- metrics are scalar JSON-friendly; heavy arrays are artifacts/references
- determinism for same config + seed

---

## 3) Recommended config schema (replace placeholder)

### Current placeholder (to be replaced)
`config.py` currently defines:

```py
class FreeSpaceCfg(StageConfig):
    name: str
    kind: Literal["treacy_grating"] = "treacy_grating"
    gdd_fs2: float = 0.0
```

This cannot match a geometry calculator and is easy to misuse.

### Replace with discriminated union
Keep a single stage type `FreeSpaceStage`, but make its config a discriminated union:

- `treacy_grating_pair`: geometry-derived coefficients (production path)
- `phase_only_dispersion`: explicit coefficients (debug / migration / synthetic tests)

**Recommended v1 configs** (pydantic v2):

```py
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from cpa_sim.phys_pipeline_compat import StageConfig

class TreacyGratingPairCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["treacy_grating_pair"] = "treacy_grating_pair"

    # Inputs (user-friendly units)
    line_density_lpmm: float         # lines/mm
    incidence_angle_deg: float       # degrees
    separation_um: float             # um (internal length unit)
    wavelength_nm: float             # nm (common spec)

    # Conventions / toggles (pin defaults to reference calculator)
    diffraction_order: int = -1
    n_passes: int = 2                # double-pass default
    include_tod: bool = True
    apply_to_pulse: bool = True

    # Optional override knobs (debug/migration)
    override_gdd_fs2: float | None = None
    override_tod_fs3: float | None = None

class PhaseOnlyDispersionCfg(StageConfig):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["phase_only_dispersion"] = "phase_only_dispersion"
    gdd_fs2: float = 0.0
    tod_fs3: float = 0.0
    apply_to_pulse: bool = True

FreeSpaceCfg = Annotated[
    TreacyGratingPairCfg | PhaseOnlyDispersionCfg,
    Field(discriminator="kind"),
]
```

### Backward-compat parsing rule
If old configs appear (e.g., `{"kind":"treacy_grating","gdd_fs2":...}`), a `model_validator(mode="before")` should:
- map to `PhaseOnlyDispersionCfg(gdd_fs2=..., tod_fs3=0)`
- emit a deprecation warning (but still run)

---

## 4) Units + conversions (make explicit)

All computations are performed in internal units (`fs/um/rad`). Inputs are converted once at parse/compute time.

### Wavelength
- input: `wavelength_nm`
- internal: `λ_um = wavelength_nm * 1e-3`

### Grating period
- input: `line_density_lpmm` (lines/mm)
- internal period (um):
  - `d_um = 1000.0 / line_density_lpmm`
  - because 1 mm = 1000 um

### Angles
- input: `incidence_angle_deg`
- internal: `θi = deg2rad(incidence_angle_deg)`

### Separation
- input: `separation_um` (already internal unit)

### Speed of light
- `c_um_per_fs = 0.299792458` (exact)

---

## 5) Treacy grating‑pair formulas (match reference)

The LaserCalculator page states it computes a **double-pass Treacy grating pair** and defines formulas using:
- `N` = number of passes (**2** for the calculator)
- `m` = diffraction order (**−1** shown)
- `λ` = center wavelength
- `d` = grating period (inverse of line density)
- `L` = physical distance between two parallel gratings
- `θi` = incidence angle

The following closed-form expressions (commonly cited) should be used in the backend to match the calculator’s conventions:

### 5.1 GDD
**Definition:** `GDD = d²φ/dω²`

\ufeff**Compute in internal units** (`λ,d,L` in um; `c` in um/fs; `ω` in rad/fs) so the result is in `fs²`:

```
GDD = - (N * m^2 * L * λ^3) / (2π * c^2 * d^2) * [ 1 - ( -m*λ/d - sin(θi) )^2 ]^(-3/2)
```

### 5.2 TOD
**Definition:** `TOD = d³φ/dω³`

```
TOD = - (3*λ)/(2π*c) * ( (1 + (λ/d)*sin(θi) - sin(θi)^2) / (1 - ( (λ/d) - sin(θi) )^2) ) * GDD
```

**Notes**
- Keep `m` explicit even though the squared `m^2` appears in GDD. The `(-m*λ/d - sin θi)` term is sign-sensitive.
- The calculator’s outputs are shown in **ps²** (for GDD) and **fs³** (for TOD), but internal metrics must remain `fs²` / `fs³`. Provide converted display metrics if useful.

---

## 6) Derived geometry metrics (optional but recommended)

These are diagnostics and should be recorded as scalar metrics for debugging sign errors.

### Littrow angle
```
θL = asin( λ / (2d) )
```

### Diffraction angle (order m)
Use the convention consistent with the reference calculator’s “order=-1” output:

```
θD = asin( sin(θi) + m*λ/d )
```

### Angular dispersion (deg/nm) (optional)
If you record it, compute from the grating equation derivative, and document the exact expression used.
(You can also omit this in v1 if it is not used by `cpa-sim` downstream.)

---

## 7) Applying spectral phase to the pulse (phase-only element)

If `apply_to_pulse=True`, apply a Taylor phase about the center frequency `ω0`:

### Definitions
```
ω0 = 2π*c/λ
Δω = ω - ω0
φ(ω) = 0.5*GDD*Δω^2 + (1/6)*TOD*Δω^3   (TOD optional)
E_out(ω) = E_in(ω) * exp(i*φ(ω))
```

### Required invariants (unit tests)
As a phase-only stage, it must preserve:
- spectral magnitude: `|E_out(ω)| == |E_in(ω)|` (within float tolerance)
- total energy (per ADR-0001 envelope normalization / FFT scaling)

---

## 8) Metrics and artifacts

### Required scalar metrics
- `unit_system: "fs_um_rad"`
- `gdd_fs2`
- `tod_fs3` (0.0 if disabled)
- `omega0_rad_per_fs`
- config echo: `lambda0_nm`, `wavelength_nm`, `line_density_lpmm`, `incidence_angle_deg`, `separation_um`, `diffraction_order`, `n_passes`

### Recommended scalar metrics
- `littrow_angle_deg`
- `diffraction_angle_deg`
- `is_valid_order` (bool)

### Artifacts (optional)
- `phi_of_omega` array (only if you already store artifacts and it’s useful)
- intermediate variables for debugging domain/sign

---

## 9) Error handling (must be explicit)

Fail fast with a clear `ValueError` when:
- no propagating diffracted order exists (asin argument outside [-1,1] or bracket term invalid)
- invalid physical inputs (non-positive wavelength, line density, separation)
- unsupported `n_passes` or `diffraction_order` (if you choose to restrict them)

Error messages must name the offending values.

---

## 10) Acceptance criteria (what “done” means)

A Treacy backend is considered correct when:

1) **Golden numeric match:** for a committed fixture set of cases, computed `GDD` and `TOD` match recorded reference outputs within specified tolerances.
2) **Invariants:** phase-only application preserves spectrum magnitude and energy.
3) **Contracts:** unit suffixes and `phys-pipeline` stage contract obeyed.
4) **Back-compat:** old placeholder configs still parse, with deprecation warning.

---

## References (for humans, not code)
- LaserCalculator “Grating pair dispersion calculator” (Treacy, double-pass; notes on passes/order/angles).
- Ibsen Photonics white paper “Pulse stretching and compressing using grating pairs” (Treacy GDD expression; mentions retroreflection doubles dispersion).
- General Treacy (1969) grating pair theory background.
