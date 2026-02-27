# fiber_amp_wrap context

## Scope
`fiber_amp_wrap` is a **simplified fiber amplifier model** for CPA chain simulations. It does not implement its own propagation solver. Instead, it is a **wrapper around existing fiber backends via `FiberStage`** and maps a user-facing average output power target into a distributed gain term.

The stage takes `power_out_w` as the required **average output power at the measurement plane** and converts that target into an effective `loss_db_per_m` passed to the delegated fiber backend.

## Non-goals
`fiber_amp_wrap` is intentionally limited.

It explicitly includes:
- gain modeled **only** as distributed gain through negative `loss_db_per_m`

It explicitly excludes:
- **NO ASE**
- **NO gain saturation**
- **NO pump dynamics**
- no inversion / rate-equation modeling
- no wavelength-dependent gain shaping beyond whatever the wrapped backend already does

## Definitions
- **Measurement plane**: in this model, the measurement plane is the **stage output plane** because we are not modeling isolators/couplers in this stage.
- `power_out_w`: requested average output power (W) at that output plane.
- `intrinsic_loss_db_per_m`: passive/background fiber attenuation already present in physics config.
- `L`: fiber length in meters.

### Normalization warning
For `power_out_w` to be physically meaningful, `|A|^2` must be in Watts. If the field normalization is not power-normalized, `power_out_w` becomes only a relative scaling target.

## Mapping (exact math)
`fiber_amp_wrap` computes the required net gain and converts it into backend-compatible loss terms using:

- `dt_s = dt_fs*1e-15`
- `E_in = sum(|A|^2)*dt_s`
- `P_in_avg = E_in * f_rep`
- `G_net = power_out_w / P_in_avg`
- `loss_eff_db_per_m = -(10/L)*log10(G_net)`
- `loss_total_db_per_m = intrinsic_loss_db_per_m + loss_eff_db_per_m`

Interpretation:
- `loss_eff_db_per_m < 0` means distributed gain.
- `loss_total_db_per_m` is what gets passed to `FiberStage` / selected backend.

## Guardrails
Fail fast if any of the following occur:
- `power_out_w <= 0`
- missing or non-positive repetition rate (`f_rep <= 0`)
- `L <= 0`
- non-positive computed input average power (`P_in_avg <= 0`)
- non-positive net gain ratio (`G_net <= 0`)
- non-finite values in mapping chain

## Tests
Recommended checks for this stage:

1. **Unit mapping test**
   - Construct a known input field and rep rate.
   - Verify computed `loss_eff_db_per_m` and `loss_total_db_per_m` match analytic values from the equations above.

2. **Wrapper delegation test**
   - Monkeypatch/stub `FiberStage`.
   - Verify `fiber_amp_wrap` forwards the modified loss coefficient and does not alter unrelated physics knobs.

3. **Power-target consistency test**
   - Use a deterministic backend setup.
   - Confirm measured output average power matches `power_out_w` within tolerance.

4. **Validation/guardrail tests**
   - Ensure invalid inputs raise clear structured errors.
