# ADR-0007: Toy fiber amp backend assumptions (v1)

- Status: Accepted
- Date: 2026-02-18

## Context

The amp stage needs a deterministic, CI-friendly backend that can model basic nonlinear amplification
behavior without introducing heavy dependencies or claiming full EDFA fidelity.

## Decision

Add a new amp backend config `kind: toy_fiber_amp` with parameters:
- `length_m`, `beta2_s2_per_m`, `gamma_w_inv_m`,
- `gain_db`, `loss_db_per_m`, `n_steps`.

Implementation uses a deterministic split-step method with distributed gain/loss and Kerr SPM.

## Assumptions and explicit non-goals

Assumptions:
- pulse intensity `|A(t)|^2` is used as a power proxy in arbitrary units,
- gain/loss are applied as distributed power coefficients and converted to field amplitude factors,
- B-integral output is a proxy: `gamma * L * peak_power_in`.

Non-goals:
- no ASE,
- no pump depletion,
- no wavelength-dependent gain.

## Validation

Validated via fast unit tests:
- gain-only energy scaling,
- SPM-induced spectral broadening,
- stretched-vs-direct reduction in B-integral proxy.
