**Title:** cpa-sim stage ownership and domain boundaries for laser, free-space, fiber, and amp.

- **ADR ID:** ADR-0004
- **Status:** Proposed
- **Date:** 2026-02-16
- **Deciders:** @cpa-sim maintainers
- **Area:** architecture
- **Related ecosystem ADRs:** ECO-0004
- **Tags:** ownership, staging, boundaries
- **Scope:** cpa-sim

### Context
`cpa-sim` is the implementation owner for CPA-stage domain logic. To avoid cross-repo drift and unclear responsibilities, this repo must explicitly own laser specification handling plus stage implementations for free-space propagation, fiber propagation, and amplification while consuming shared pipeline contracts from upstream orchestration repos.

### Decision
Within the CPA ecosystem, `cpa-sim` owns:

1. **Laser spec and initialization domain**
   - Validation/normalization of input laser specs used to construct initial pulse state.
   - Deterministic initialization (including seeded behaviors where applicable).
2. **Free-space stage domain**
   - Stretcher/compressor free-space models and their convention-sign validation.
3. **Fiber stage domain**
   - Fiber propagation stage integration (v1 via external solver wrappers, later via in-house backend).
4. **Amp stage domain**
   - Amplification stage configuration and gain-model implementations.

`cpa-sim` must not redefine generic pipeline abstractions from `phys-pipeline`; it consumes them and provides domain stage implementations.

### Consequences
- **Positive:** clear domain authority for CPA physics implementation and ADR-driven change control.
- **Negative:** broader ownership in one repo increases review burden for cross-stage changes.
- **Implementation follow-up:** keep ADR references in stage module docs and update STATUS/roadmap when responsibilities evolve.

### Validation
- Stage-level tests exist for each governed domain: laser init, free-space, fiber, amp.
- Integration tests cover end-to-end chain behavior and schema-compliant outputs.
- Boundary reviews reject changes that attempt to shift domain logic to unrelated repos.

### References
- `cpa-architecture/docs/adr/ECO-0004-repository-roles-boundaries.md`
- `cpa-architecture/docs/SYSTEM_OVERVIEW.md`
