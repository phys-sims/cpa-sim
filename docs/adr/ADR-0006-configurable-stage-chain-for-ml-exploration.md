**Title:** Introduce configurable stage-chain composition while preserving v1 defaults.

- **ADR ID:** ADR-0006
- **Status:** Accepted
- **Date:** 2026-02-17
- **Deciders:** @cpa-sim maintainers
- **Area:** architecture
- **Tags:** config, pipeline, ml, topology
- **Scope:** cpa-sim pipeline configuration

### Context
The fixed v1 chain (`laser_gen -> free_space -> fiber -> amp -> free_space -> metrics`) is a good baseline, but it is too rigid for exploration workflows and ML-driven search where stage sequences can vary (e.g., no stretcher, repeated fiber+amp blocks, alternate compressor placement).

### Decision
Add a stage-bank + stage-chain config model:
- stage banks keyed by stage type (`laser_gen_stages`, `free_space_stages`, `fiber_stages`, `amp_stages`, `metrics_stages`)
- explicit ordered `stage_chain` references (`stage_type`, `key`)

`PipelineConfig` keeps legacy single-stage keys (`stretcher`, `fiber`, `amp`, `compressor`, etc.) and auto-populates stage banks and default chain for backward compatibility.

### Constraints
- Chain must start with `laser_gen` and end with `metrics`.
- Every `stage_chain` reference key must exist in the corresponding stage bank.
- Execution remains sequential and deterministic for fixed config + seed.

### Consequences
- **Positive:** supports optional or repeated stage combinations without API breakage.
- **Positive:** enables ML/testharness to search topology and parameter space via one config surface.
- **Negative:** config validation complexity increases; must keep error messages explicit.

### Validation
- Integration test: legacy default chain still runs.
- Integration test: custom chain without initial free-space stage and with repeated fiber+amp pairs runs and emits expected namespaced metrics.

### References
- `docs/adr/ADR-0005-phys-pipeline-contract-adoption.md`
- `docs/agent/phys-pipeline-context.md`
