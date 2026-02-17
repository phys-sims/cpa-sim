**Title:** Adopt phys-pipeline contracts as the canonical execution substrate for cpa-sim.

- **ADR ID:** ADR-0005
- **Status:** Accepted
- **Date:** 2026-02-17
- **Deciders:** @cpa-sim maintainers
- **Area:** architecture
- **Tags:** pipeline, contracts, reproducibility, integration
- **Scope:** cpa-sim core runtime

### Context
`cpa-sim` requires a stable stage/pipeline substrate with deterministic execution, typed stage interfaces, and extensible provenance/artifact handling. Re-implementing these primitives in-repo would duplicate capability already provided by `phys-pipeline` and create drift risk between repos.

### Decision
`cpa-sim` adopts `phys-pipeline` primitives directly as foundational runtime contracts:

- `State`
- `StageConfig`
- `StageResult`
- `PipelineStage`
- `SequentialPipeline`
- `PolicyBag`

The CPA simulator owns **domain models** (`LaserSpec`, `LaserState`, pulse/beam structures) and stage implementations, while execution semantics and contract types are sourced from `phys-pipeline`.

### Constraints and boundary rules
- Do not redefine equivalent pipeline primitives in `cpa-sim`.
- External solver boundaries remain in stage backend modules (`stages/<type>/<backend>.py`).
- `metrics` remain scalar JSON-friendly; heavy arrays are artifacts/references.
- Determinism is required for identical config + seed.

### Consequences
- **Positive:** shared behavior and API expectations across simulation repos; lower maintenance overhead.
- **Positive:** direct compatibility with future phys-pipeline upgrades (DAG, scheduler, cache) as additive layers.
- **Negative:** runtime environments must provide a compatible `phys-pipeline` installation.
- **Mitigation:** maintain a compatibility import surface that prefers canonical imports and fails with clear errors when unavailable.

### Validation
- Unit test for deterministic runs with same config/seed.
- Integration test for tiny full CPA chain execution and finite summary metrics.
- Required CI gates (`pre-commit`, `mypy`, fast pytest markers) must pass.

### References
- `docs/agent/phys-pipeline-context.md`
- `docs/adr/ADR-0002-result-schema-contract.md`
- `docs/adr/ADR-0004-stage-domain-boundaries.md`
