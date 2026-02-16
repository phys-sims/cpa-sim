# SIM-ADR-0004: Adopt ECO-0004 repository boundary and ownership model in cpa-sim

- **Status:** Proposed
- **Date:** 2026-02-16
- **Mapped ecosystem ADR:** [ECO-0004](../../../../docs/adr/ECO-0004-repository-roles-boundaries.md)

## Decision
Adopt ECO-0004 in `cpa-sim` as the governing statement of repository role, ownership boundaries, and cross-repo integration expectations.

## Inherited from ecosystem ADR (verbatim vs summarized)
Source of truth is ECO-0004; this ADR records repository-level adoption only.

Inherited policy summary:
- Respect ecosystem repository boundaries for code ownership and responsibility.
- Keep shared contracts and cross-repo interfaces aligned with designated owning repos.
- Route cross-repo changes through documented coordination/publication workflow.
- Avoid local policy drift on role boundaries without ecosystem-level ADR updates.

## Repo-local extension/override
No repo-local extension at this time.

## Implications for this repo
- `cpa-sim` contributions should remain scoped to simulation-domain ownership responsibilities.
- Cross-repo contract changes initiated here should be coordinated via ecosystem workflows and ADR references.
- Local docs should acknowledge upstream ownership for shared interfaces and policies.

## Migration notes
- `STATUS.md` should track cleanup of any placeholder ownership notes to align with ECO-0004 terminology.
- `docs/roadmaps/v1_to_v3_plan.md` should reference this adoption ADR for repo-boundary assumptions in planning items.

## References
- Ecosystem source of truth: [ECO-0004 Repository roles and boundaries](../../../../docs/adr/ECO-0004-repository-roles-boundaries.md)
- Local status tracker: [`STATUS.md`](../../STATUS.md)
- Local roadmap: [`docs/roadmaps/v1_to_v3_plan.md`](../roadmaps/v1_to_v3_plan.md)
