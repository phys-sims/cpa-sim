**Title:** Canonical `result.json` schema contract for cpa-sim runs.

- **ADR ID:** ADR-0002
- **Status:** Proposed
- **Date:** 2026-02-16
- **Deciders:** @cpa-sim maintainers
- **Area:** io-contract
- **Related ecosystem ADRs:** ECO-0001, ECO-0002
- **Tags:** api, schema, provenance, testing
- **Scope:** cpa-sim

### Context
`cpa-sim` produces outputs consumed by harnesses and testbench workflows. The simulator must emit one predictable result shape regardless of specific stage/backend combinations (laser init, free-space, fiber, amp) so downstream tooling does not require per-backend parsing logic.

### Decision
Adopt the ECO-0002 canonical result surface for `cpa-sim`, with `schema_version: "cpa.result.v0.1"` and required top-level keys:

- `schema_version`
- `status` (`ok` or `failed`)
- `unit_system`
- `run_id`
- `timestamp_utc`
- `config_hash`
- `provenance`
- `summary`
- `metrics`
- `artifacts`
- `stages`
- `error` (required when `status=failed`)

### Artifact and stage policy
- Large arrays (fields, spectra, temporal traces) are written as file artifacts and referenced by path.
- `metrics` remains scalar-only for dashboards and optimization loops.
- Stage records must include stage identity, stage config hash, scalar metrics, and artifact references.
- Add an additive `observables` contract (schema `cpa.observables.v0.1`) that separates latent simulation arrays from measured scalar observables with explicit method/assumption tags.

### Observable contract (additive)
- **Latent simulation state** (`field_t`, `field_w`, grid axes/units) remains in internal stage state and array artifacts; these are not treated as direct measured outputs.
- **Measured observables** are emitted as a structured list where each measurement includes:
  - `name` (e.g., `intensity_fwhm`, `intensity_autocorrelation_fwhm`, `spectral_rms_width`)
  - `value` and `unit`
  - `method` (calculation procedure)
  - `assumptions` (explicit interpretation caveats)
- Existing scalar `metrics` keys remain valid for backwards compatibility; `observables` is additive and preferred for method-aware reporting.

### Failure semantics
Failed runs must still emit schema-valid `result.json` with actionable `error` metadata and any available partial stage outputs.

### Consequences
- **Positive:** deterministic ingestion for CI, sweeps, and cross-repo tooling.
- **Negative:** schema evolution requires explicit governance and compatibility tests.
- **Implementation follow-up:** add a pydantic/json-schema model and fixture-based compatibility tests.

### Validation
- Schema model tests for required keys/types.
- Success and failure fixture validation tests.
- Adapter ingestion tests that consume only canonical keys.

### References
- `cpa-architecture/docs/adr/ECO-0002-result-schema-contract.md`
