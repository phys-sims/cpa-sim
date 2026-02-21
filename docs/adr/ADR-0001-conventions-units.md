**Title:** cpa-sim conventions and units contract for CPA state and stage interfaces.

- **ADR ID:** ADR-0001
- **Status:** Proposed
- **Date:** 2026-02-16
- **Deciders:** @cpa-sim maintainers
- **Area:** simulation-core
- **Related ecosystem ADRs:** ECO-0001, ECO-0002
- **Tags:** api, data-model, physics, testing
- **Scope:** cpa-sim

### Context
`cpa-sim` is the implementation authority for CPA simulation stages spanning laser specification initialization, free-space propagation, fiber propagation, and amplification. To keep these stage boundaries numerically consistent and deterministic, we need one explicit convention set for units, FFT scaling, chirp/dispersion signs, and metric naming that matches ecosystem contracts.

### Decision
Adopt the ECO-0001 convention set for all internal `cpa-sim` calculations and external contract surfaces:

1. **Internal units:** `fs`, `um`, `rad`; angular frequency in `rad/fs`; speed of light `c = 0.299792458 um/fs`.
2. **Boundary declaration:** outputs and config-normalized artifacts declare `unit_system: "fs_um_rad"`.
3. **Metric naming:** dimensional metric keys use explicit suffixes (`_fs`, `_um`, `_rad_per_fs`, `_j`, `_w`).
4. **Envelope normalization:** the complex envelope is represented in `sqrt(W)` so `|E|^2` is power in `W`; energy integrates as `sum(|E|^2 * dt_fs * 1e-15)`.
5. **FFT/scaling:** use NumPy FFT sign convention with explicit time-step scaling (`Ew = dt_s * FFT(Et)`, `Et = (1/dt_s) * IFFT(Ew)`).
6. **Sign conventions:** positive chirp means `dω_inst/dt > 0`; GDD sign follows `d²φ/dω²`; free-space grating equation signs are documented and tested per backend.
7. **Observable/latent split:** latent complex fields (`field_t`, `field_w`) remain simulation state, while reported observables (e.g., FWHM/autocorrelation/spectral width) must declare method and assumptions in an observable contract surface.

### Consequences
- **Positive:** laser, free-space, fiber, and amp stages can share one stable state contract without hidden conversions.
- **Negative:** all new metrics and adapters must comply with suffix/unit rules.
- **Implementation follow-up:** add invariant tests for phase-only energy preservation and sign-convention fixtures for free-space/fiber.

### Validation
- Unit tests for unit suffix policies and envelope-energy invariants.
- Integration tests across stretcher → fiber → amp → compressor with deterministic seeds.
- Physics tests that pin free-space and fiber sign-sensitive metrics.

### References
- `cpa-architecture/docs/adr/ECO-0001-conventions-units.md`
- `cpa-architecture/docs/adr/ECO-0002-result-schema-contract.md`
