# Fiber Stage Context (Strategy B + WUST‑FOG GNLSE backend)

**Last updated:** 2026-02-16  
**Owner:** Ryaan Lari  
**Audience:** coding agents + future maintainers

## 0) Purpose

This document is the **single source of truth** for implementing the FiberStage using **Strategy B**:

- A **stable, backend-agnostic** `FiberPhysicsCfg` (“what physics is being modeled”)
- A **backend-specific** `FiberNumericsCfg` union (“how to numerically solve it”), including a **WUST‑FOG gnlse-python** backend.

This is explicitly designed so that:
- `cpa-sim` can ship **now** with WUST‑FOG `gnlse` as a backend,
- and later swap/add an in-house “variable fidelity / ML-native” GNLS solver **without breaking the public interface**.

This doc also defines how `LaserState` must evolve to support both:
- fiber propagation (pulse-only),
- free-space stretcher/compressor stages (pulse + beam).

---

## 1) Non-goals (avoid scope creep)

- Don’t implement the in-house GNLS solver here.
- Don’t refactor unrelated stage APIs.
- Don’t attempt “full fidelity” fiber modeling (PMD, polarization, multimode, gain) unless explicitly enabled later.
- Don’t silently change pulse normalization without surfacing it in state metadata.

---

## 2) Strategy B (the design you must implement)

### 2.1 The core idea

**Physics config stays stable** and describes the *physical medium and effects*.

**Numerics config is a discriminated union** keyed by `backend` and is allowed to mirror upstream solver knobs closely.

That gives you:
- *stability* for users and downstream code (optimizers, ML tooling),
- *flexibility* to wrap third-party solvers without contaminating physics APIs,
- and a clean path to a future in-house solver.

### 2.2 What “stable” means here

`FiberPhysicsCfg` is the long-lived API. It should contain:
- fiber length, loss,
- dispersion parameters,
- nonlinearity parameters,
- toggles for Raman / self-steepening,
- and (optionally) a consistent way to define gamma via material + mode area.

It should **NOT** contain solver method names, ODE tolerances, snapshot counts, etc.

### 2.3 What “backend-specific” means here

`FiberNumericsCfg` is a union with entries like:
- `ToyPhaseNumericsCfg` (your current stub / very fast baseline)
- `WustGnlseNumericsCfg` (this doc)
- `InHouseGnlseNumericsCfg` (future)

Each backend config can:
- be as close as possible to its solver’s parameterization,
- add grid policy knobs (resample, enforce pow2),
- and control artifact retention.

---

## 3) LaserState / PulseState / BeamState: required shape & invariants

### 3.1 LaserState must contain PulseState and BeamState
Fiber stages operate primarily on `PulseState`, and free-space stages need both.

**Hard rule:** FiberStage **must not delete or invalidate BeamState**. If the fiber backend does not model beam changes, BeamState passes through unchanged.

### 3.2 Pulse normalization must be explicit
A GNLS solver needs **physical scaling** to be meaningful (e.g., SPM depends on absolute power).

You must choose one canonical convention and carry it through:

**Recommended canonical convention (do this):**
- `pulse.field_t` is the **envelope amplitude** with units **sqrt(W)** such that:
  - instantaneous power `P(t) = |A(t)|^2` in watts
  - pulse energy `E = ∫ |A(t)|^2 dt` in joules (with dt in seconds)

Store this explicitly in state metadata:
- `pulse.meta["field_units"] = "sqrt(W)"`
- `pulse.meta["power_is_absA2_W"] = True`

If the codebase currently uses a dimensionless normalization, you have two options:
1) **Migrate now** to sqrt(W) and fix upstream stages accordingly (best long-term).
2) **Bridge**: keep internal dimensionless fields but require `PulseState` to provide a scaling factor like:
   - `pulse.power_scale_w` meaning `P(t) = power_scale_w * |A_dimless(t)|^2`
   - and the wrapper must scale before calling GNLS, then scale back after.

**If you pick option (2)**, you must still set metadata so downstream code knows what it’s looking at.

This document assumes the recommended canonical convention (sqrt(W)).
If your code still uses dimensionless, implement option (2) as a temporary bridge but keep the public interface identical.

### 3.3 Grid invariants
WUST‑FOG `gnlse` uses:
- `resolution` points
- `time_window` (ps)
- and builds its own uniform time grid.

Your `PulseGrid` likely already represents a uniform grid.

**Hard rules:**
- The wrapper must verify uniform spacing (within tolerance).
- The wrapper must not silently change resolution unless `numerics.grid_policy` explicitly allows it.

---

## 4) Public configs (Pydantic) — canonical schemas

> Names can be adjusted to match your repo style, but the structure must match this.

### 4.1 FiberStageCfg (top-level stage cfg)

```python
class FiberStageCfg(BaseModel):
    kind: Literal["fiber"] = "fiber"
    physics: FiberPhysicsCfg
    numerics: FiberNumericsCfg  # discriminated union
```

### 4.2 FiberPhysicsCfg (stable)

```python
class FiberPhysicsCfg(BaseModel):
    # Geometry / length
    length_m: float

    # Loss
    loss_db_per_m: float = 0.0

    # Nonlinearity (choose ONE of these ways to define gamma)
    gamma_1_per_w_m: float | None = None  # direct gamma
    # optional "derive gamma" path for future expansion:
    n2_m2_per_w: float | None = None
    aeff_m2: float | None = None

    # Dispersion (union so we can support Taylor OR interpolation)
    dispersion: DispersionCfg

    # Effects toggles (stable across backends)
    raman: RamanCfg | None = None
    self_steepening: bool = False

    # Validation policy (helps keep agent work safe)
    validate_physical_units: bool = True
```

### 4.3 DispersionCfg (stable union)

```python
class DispersionTaylorCfg(BaseModel):
    kind: Literal["taylor"] = "taylor"
    # betas in ps^n / m, typically [beta2, beta3, ...]
    betas_psn_per_m: list[float]

class DispersionInterpolationCfg(BaseModel):
    kind: Literal["interpolation"] = "interpolation"
    neff: list[float]                 # effective indices
    lambdas_nm: list[float]           # wavelengths in nm
    central_wavelength_nm: float      # pump wavelength nm

DispersionCfg = Annotated[
    Union[DispersionTaylorCfg, DispersionInterpolationCfg],
    Field(discriminator="kind"),
]
```

### 4.4 RamanCfg (stable, stringly-typed on purpose)

```python
class RamanCfg(BaseModel):
    kind: Literal["wust"] = "wust"  # today this maps to WUST function names
    model: Literal["blowwood", "linagrawal", "hollenbeck"]
```

### 4.5 FiberNumericsCfg (backend-specific union)

```python
class ToyPhaseNumericsCfg(BaseModel):
    backend: Literal["toy_phase"] = "toy_phase"
    # maintain your current stub behavior as a cheap baseline
    nonlinear_phase_rad: float = 0.0

class WustGnlseNumericsCfg(BaseModel):
    backend: Literal["wust_gnlse"] = "wust_gnlse"

    # ---- grid policy ----
    # "use_state" = use LaserState grid as-is
    # "force_pow2" = resample to nearest power-of-two resolution (explicitly)
    # "force_resolution" = resample to exactly resolution_override
    grid_policy: Literal["use_state", "force_pow2", "force_resolution"] = "use_state"
    resolution_override: int | None = None
    time_window_override_ps: float | None = None

    # ---- solver controls (mirror upstream) ----
    z_saves: int = 200
    method: str = "RK45"
    rtol: float = 1e-5
    atol: float = 1e-8

    # ---- output / artifact policy ----
    keep_full_solution: bool = False     # store intermediate z traces as artifact
    keep_aw: bool = True                 # store final spectral field_w in state
    record_backend_version: bool = True  # store pip/git version strings in artifacts

FiberNumericsCfg = Annotated[
    Union[ToyPhaseNumericsCfg, WustGnlseNumericsCfg],
    Field(discriminator="backend"),
]
```

---

## 5) The WUST‑FOG `gnlse` backend: what you must know

### 5.1 Upstream references
- GitHub repo: `https://github.com/WUST-FOG/gnlse-python`
- Docs: `https://gnlse.readthedocs.io/`
- PyPI package: `gnlse`

**Version reality check (important):**
- PyPI currently lists `gnlse==2.0.0` as the released distribution.
- The GitHub README mentions a `v2.0.1` release date; it may not be published to PyPI.

**Actionable recommendation:**
- Default to **PyPI `gnlse==2.0.0`** for reproducible installs.
- If you need GitHub-only features, pin via:
  - `pip install "gnlse @ git+https://github.com/WUST-FOG/gnlse-python@<tag_or_sha>"`

### 5.2 Required upstream units (must convert)
From upstream docs, GNLSESetup expects:
- `time_window` in **ps**
- `wavelength` in **nm**
- `fiber_length` in **m**
- `nonlinearity` in **1/(W·m)**
- dispersion Taylor betas in **ps^n / m**
- loss in **dB / m**

### 5.3 Mapping table: LaserState + FiberPhysicsCfg -> GNLSESetup

Assume `LaserState.pulse.grid` defines a uniform time axis in **fs** and center wavelength in **nm**.

| CPA-Sim | WUST gnlse | Conversion |
|---|---|---|
| `N = len(pulse.grid.t_fs)` | `setup.resolution = N` | exact |
| `T_fs = (t_fs[-1] - t_fs[0])` | `setup.time_window = T_fs / 1000` | fs → ps |
| `pulse.grid.center_wavelength_nm` | `setup.wavelength` | nm passthrough |
| `physics.length_m` | `setup.fiber_length` | m passthrough |
| `physics.loss_db_per_m` | dispersion model `loss` | dB/m passthrough |
| `physics.gamma_1_per_w_m` | `setup.nonlinearity` | 1/(W·m) passthrough |
| `pulse.field_t` (sqrt(W)) | `setup.pulse_model` (complex array) | passthrough (ensure length N) |
| `physics.dispersion.kind == "taylor"` | `DispersionFiberFromTaylor(loss, betas)` | betas list in ps^n/m |
| `physics.dispersion.kind == "interpolation"` | `DispersionFiberFromInterpolation(...)` | pass neff/lambdas/central λ |
| `physics.raman.model` | `setup.raman_model = gnlse.raman_<model>` | string → function |
| `physics.self_steepening` | `setup.self_steepening` | passthrough |

### 5.4 Grid policy and “avoid large prime factors”
Upstream docs warn to avoid resolutions with large prime factors.

**Default behavior (safe):**
- if `grid_policy == "use_state"`: do not resample; just warn in logs if `N` is “bad”
- if `grid_policy == "force_pow2"`: resample to nearest power of two (document it in artifacts)
- if `grid_policy == "force_resolution"`: resample to `resolution_override` (must be provided)

**Resampling requirement:**
If you resample, do it in the time domain:
- create new uniform `t` grid over the same time window
- interpolate complex `field_t` (real+imag separately) or resample in frequency domain carefully
- update `PulseGrid` accordingly

No silent resampling.

### 5.5 Output mapping: Solution -> LaserState
`gnlse.GNLSE.run()` returns a `Solution` with:
- `t` (ps), `W` (angular frequency grid), `Z` (m), `At`, `AW`

**Minimum update required:**
- Set `pulse.field_t = At_final` (convert time axis back to fs if you are reconstructing grid)
- Compute/update `pulse.intensity_t = abs(field_t)**2`
- If `keep_aw`:
  - Set `pulse.field_w` from the final `AW` (but ensure FFT conventions match your `PulseGrid`)
  - Set `pulse.spectrum_w = abs(field_w)**2`

**Best practice:**
Even if you have `AW`, recompute `field_w` using your project’s canonical FFT helper to avoid convention mismatch.

### 5.6 Amplitude scaling pitfalls
If `pulse.field_t` is not sqrt(W), SPM strength, Raman, etc. will be nonsense.

If you cannot migrate to sqrt(W immediately:
- require a scaling factor in `PulseState` metadata and scale before/after calling gnlse
- record this in artifacts:
  - `artifacts["fiber.wust.scale_mode"] = "dimless_to_sqrtW"`
  - `artifacts["fiber.wust.power_scale_w"] = "<float>"`

---

## 6) Where this code should live (recommended repo layout)

Assuming you already have something like `src/cpa_sim/stages/fiber/glnse_wrap.py` as a stub.

Recommended structure:

```
src/cpa_sim/stages/fiber/
  __init__.py
  fiber_stage.py              # FiberStage orchestrator (selects backend)
  backends/
    __init__.py
    toy_phase.py              # current cheap stub backend
    wust_gnlse.py             # this integration
  utils/
    grid.py                   # resampling, uniform checks, prime-factor warnings
    units.py                  # fs<->ps, etc.
```

**Key rule:** `fiber_stage.py` should contain zero upstream-specific imports. All third-party imports belong inside the backend module and should be lazy-imported.

---

## 7) Backend interface (internal protocol)

Define a thin internal protocol so backends are interchangeable:

```python
class FiberBackend(Protocol):
    def run(self, state: LaserState, physics: FiberPhysicsCfg, numerics: BaseModel) -> StageResult[LaserState]:
        ...
```

`FiberStage`:
- validates invariants (grid, units, required physics fields),
- dispatches to backend based on `cfg.numerics.backend`,
- attaches provenance artifacts.

---

## 8) Packaging & optional dependencies

### 8.1 Make gnlse optional
Do not make `gnlse` a hard dependency of `cpa-sim` unless you want every install to drag in `pyfftw`.

Use extras in `pyproject.toml`:

- `cpa-sim[gnlse]` installs `gnlse` + any required numeric deps.

Example intent (adjust versions as needed):
- `gnlse==2.0.0`
- `pyfftw` (transitive)
- OS-level FFTW may be required in CI (e.g., `libfftw3-dev` on Ubuntu).

### 8.2 Lazy import pattern
In `wust_gnlse.py`:

- import `gnlse` inside the `run()` function (or inside a helper called by run)
- if import fails, raise a clean error explaining:
  - install extras
  - or switch numerics backend to `toy_phase`

---

## 9) Testing requirements (don’t skip this)

### 9.1 Unit tests (fast, always-on)
1) **Grid uniformity check**
   - construct a grid with tiny jitter and confirm it errors
2) **fs→ps conversion correctness**
   - assert `time_window_ps == time_window_fs / 1000`
3) **Config validation**
   - missing `length_m` or missing `gamma` must raise
4) **No silent resampling**
   - when `grid_policy == "use_state"`, `PulseGrid.N` must be unchanged

### 9.2 Integration tests (optional dependency; mark as slow)
These require `gnlse` installed.

Recommended approach: reproduce invariants from upstream examples but at **small resolution**.

Minimum integration tests:
1) **SPM-only sanity**
   - dispersion off, loss=0
   - gamma>0, short fiber
   - check:
     - energy roughly conserved (within tolerance)
     - spectrum broadens vs input (e.g., RMS bandwidth increases)
2) **GVD-only sanity**
   - gamma=0, nonzero beta2
   - check:
     - temporal broadening occurs (RMS duration increases)
3) **Raman toggle sanity**
   - enable Raman model, ensure run completes and produces finite output

### 9.3 Numerical tolerances (be realistic)
These are stiff simulations. Don’t assert exact curves.
Assert invariants and monotonic trends:
- energy approximately conserved if loss=0
- finite outputs
- broadening trends
- shape changes qualitatively

---

## 10) Artifacts & provenance (required for debugging + caching)

FiberStage should attach artifacts/metrics like:

- `metrics["fiber.energy_in_j"]`, `metrics["fiber.energy_out_j"]`
- `metrics["fiber.spectral_rms_in"]`, `metrics["fiber.spectral_rms_out"]`
- `artifacts["fiber.backend"] = "wust_gnlse"`
- `artifacts["fiber.gnlse.version"] = "<pip version or git sha>"` (if enabled)
- `artifacts["fiber.grid_policy"] = "<...>"`

If `keep_full_solution`:
- store `Z` and maybe downsampled `At`/`AW` traces to a file (npz/h5) and link via artifacts path
- do **not** store huge arrays inline in the state object

---

## 11) Future in-house solver: how Strategy B keeps you safe

When you build `glnse-sim` (your future variable-fidelity, ML-native solver), you should:
- keep `FiberPhysicsCfg` identical
- add a new `InHouseGnlseNumericsCfg(backend="inhouse_gnlse", ...)`
- implement a new backend module
- reuse the same test invariants so you can compare solvers apples-to-apples

This is the whole point of Strategy B: backend swaps become mechanical, not invasive.

---

## 12) Implementation checklist pointer

Execution checklist lives here (separate file):
- `docs/agent/fiber-stage-roadmap.md`

Keep this file stable; update roadmap as work progresses.
