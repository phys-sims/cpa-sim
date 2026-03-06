# ADR Index

| ADR | Title | Status | Date | Area | Tags |
|---:|---|---|---|---|---|
| [ADR-0001](ADR-0001-conventions-units.md) | cpa-sim conventions and units contract for CPA state and stage interfaces | Proposed | 2026-02-16 | simulation-core | api, data-model, physics, testing |
| [ADR-0002](ADR-0002-result-schema-contract.md) | Canonical `result.json` schema contract for cpa-sim runs | Proposed | 2026-02-16 | io-contract | api, schema, provenance, testing |
| [ADR-0003](ADR-0003-validation-tiers-ci-policy.md) | Validation tiers and CI marker policy for cpa-sim | Proposed | 2026-02-16 | testing | ci, testing, reproducibility |
| [ADR-0004](ADR-0004-stage-domain-boundaries.md) | cpa-sim stage ownership and domain boundaries for laser, free-space, fiber, and amp | Proposed | 2026-02-16 | architecture | ownership, staging, boundaries |
| [ADR-0005](ADR-0005-phys-pipeline-contract-adoption.md) | Adopt phys-pipeline contracts as the canonical execution substrate for cpa-sim | Accepted | 2026-02-17 | architecture | pipeline, contracts, reproducibility, integration |
| [ADR-0006](ADR-0006-fiber-stage-physics-numerics-split.md) | Split FiberStage config into stable physics and backend numerics | Proposed | 2026-02-16 | cpa-sim | api, data-model, performance, testing, reproducibility |
| [ADR-0008](ADR-0008-canonical-output-layout.md) | Canonical run output layout and legacy filename migration | Accepted | 2026-02-21 | io-contract | cli, artifacts, compatibility |
| [ADR-0009](ADR-0009-plot-policy-namespace-determinism.md) | Plot policy namespace, default windowing/normalization, and determinism expectations | Accepted | 2026-03-06 | plotting-policy | plotting, policy, determinism, validation |
