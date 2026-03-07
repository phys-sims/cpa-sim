# cpa-sim documentation

Welcome to the documentation site for **cpa-sim**, a modular chirped-pulse amplification (CPA) simulator.

## Start here

- Read the [project README](https://github.com/phys-sims/cpa-sim/blob/main/README.md) for installation and CLI/API quickstart instructions.
- Browse canonical workflows under [Examples](examples/simple-fiber-dispersion.md).
- Review architecture and policy decisions in [ADRs](adr/INDEX.md).

## Documentation map

### Examples

- [Simple Fiber Dispersion](examples/simple-fiber-dispersion.md)
- [Wave Breaking Raman](examples/wave-breaking-raman.md)
- [Fiber Amp SPM](examples/fiber-amp-spm.md)
- [Treacy Stage Validation](examples/treacy-stage-validation.md)
- [End-to-End 1560nm](examples/end-to-end-1560nm.md)

### Configuration

- [Pulse specification reference](config/pulse_spec.md)

### Architecture decision records (ADRs)

- [ADR index](adr/INDEX.md)
- [ADR-0001: Conventions and units](adr/ADR-0001-conventions-units.md)
- [ADR-0002: Result schema contract](adr/ADR-0002-result-schema-contract.md)
- [ADR-0003: Validation tiers and CI policy](adr/ADR-0003-validation-tiers-ci-policy.md)
- [ADR-0004: Stage domain boundaries](adr/ADR-0004-stage-domain-boundaries.md)
- [ADR-0005: phys-pipeline contract adoption](adr/ADR-0005-phys-pipeline-contract-adoption.md)
- [ADR-0006: Fiber stage physics/numerics split](adr/ADR-0006-fiber-stage-physics-numerics-split.md)
- [ADR-0008: Canonical output layout](adr/ADR-0008-canonical-output-layout.md)

### Internal context and plans

- [Agent context](agent/phys-pipeline-context.md)
- [Roadmap docs](roadmaps/v1_to_v3_plan.md)
