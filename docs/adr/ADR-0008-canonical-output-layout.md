**Title:** Canonical run output layout and legacy filename migration.

- **ADR ID:** ADR-0008
- **Status:** Accepted
- **Date:** 2026-02-21
- **Deciders:** @cpa-sim maintainers
- **Area:** io-contract
- **Related ADRs:** ADR-0002
- **Tags:** cli, artifacts, compatibility
- **Scope:** cpa-sim

### Context
CLI users need one predictable on-disk layout for metrics, plots, and optional state dumps. Existing outputs used split metric files (`metrics_overall.json`, `metrics_stages.json`) and `artifacts_index.json`, which complicates downstream consumers and weakens discoverability.

### Decision
For `cpa-sim run config.yaml --out out/`, define a canonical layout under `out/`:

- `metrics.json` (required)
  - schema version: `cpa.metrics.v1`
  - keys:
    - `overall` (flat metric map)
    - `per_stage` (stage-grouped metric map)
- `artifacts.json` (required)
  - schema version: `cpa.artifacts.v1`
  - key `paths` mapping artifact names to file paths
- `stage_plots/` (required by default CLI behavior)
  - per-stage files:
    - `<stage_name>_time_intensity.svg`
    - `<stage_name>_spectrum.svg`
- `state_final.npz` (optional)
  - emitted only when `--dump-state-npz` is passed

The `.npz` payload stores canonical final-state arrays (`t`, `w`, complex field components, intensity/spectrum) plus JSON-encoded `meta`, `metrics`, and `artifacts` snapshots.

### Compatibility and deprecation policy
Legacy files remain written for compatibility in this release:

- `metrics_overall.json`
- `metrics_stages.json`
- `artifacts_index.json`

When legacy files are emitted, CLI raises a `DeprecationWarning`. Consumers should migrate to `metrics.json` and `artifacts.json`.

### Consequences
- **Positive:** single source of truth for run outputs; easier parser contracts for integration and testbench repos.
- **Positive:** explicit optional state dump policy keeps baseline artifacts bounded.
- **Tradeoff:** temporary duplication while migration window is open.

### Validation
- Integration tests assert exact canonical filenames.
- Integration tests verify required keys in `metrics.json` and `artifacts.json`.
- Integration tests verify per-stage plot filenames.
- Integration tests verify optional `state_final.npz` contents and artifact registration.
