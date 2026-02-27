# fiber_amp_wrap: measurement-plane average power amplifier wrapper (NO ASE / NO saturation)

This document defines the **fiber_amp_wrap** stage in `cpa-sim`.

**fiber_amp_wrap is NOT an EDFA model.**
It is a *simplified* amplifier representation that:
- takes a **lab-friendly output power target** (`power_out_w`, average power in Watts),
- computes the **distributed gain** required to reach that target, and
- delegates the actual propagation (dispersion, Kerr, Raman, etc.) to an existing **FiberStage backend**.

## 0) Scope and non-goals

### In scope
- User sets **`power_out_w`**: average output power **at the measurement plane** (Watts).
- Stage computes an *effective distributed gain* and converts it into a backend-compatible
  **net loss coefficient** (`loss_db_per_m`, allowing negative values).
- Delegation: propagation is performed by the configured fiber backend via `FiberStage` using `FiberCfg`.

### Explicit non-goals (this stage does NOT do these)
- **ASE noise**
- **gain saturation**
- pump dynamics, rate equations, inversion
- wavelength-dependent gain spectra
- amplifier transient behavior

If you need any of the above, this stage is the wrong tool.

---

## 1) Definitions & conventions

### Measurement plane
- `power_out_w` is defined at the **measurement plane**.
- In v1, since we do not model couplers/isolators/etc., the **measurement plane == stage output plane**.

If your lab measures after extra optics, model that with explicit loss stages.

### Repetition rate requirement
Mapping average power ↔ per-pulse energy requires repetition rate:
- `state.meta["rep_rate_mhz"]` must be present and > 0.

\[
f_\text{rep} = \text{rep_rate_mhz} \times 10^6 \quad [\text{Hz}]
\]

### Field normalization requirement (important)
For `power_out_w` to be physically meaningful in Watts, the simulation must use:
- \(|A(t)|^2\) = instantaneous power in Watts
- `dt` is converted to seconds

Otherwise `power_out_w` becomes a *relative scale knob*, not a physical watt value.

---

## 2) Backend convention: gain via negative loss_db_per_m

Backends like WUST-FOG-style GNLSE accept a **power loss coefficient** in dB/m:

\[
\frac{P_\text{out}}{P_\text{in}} = 10^{-\text{loss}\,L/10}
\]

So:
- `loss_db_per_m > 0` → attenuation
- `loss_db_per_m < 0` → distributed gain

fiber_amp_wrap exploits this: it computes the net loss_db_per_m required to hit the target output power.

---

## 3) Runtime mapping: power_out_w → loss_db_per_m

Given:
- complex time-domain field `field_t`
- time step `dt_fs` from `state.pulse.grid.dt` (fs)
- fiber length `L = cfg.physics.length_m`
- intrinsic passive loss `loss_intrinsic = cfg.physics.loss_db_per_m` (dB/m)
- `power_out_w` target

### Step 1 — pulse energy
\[
dt_s = dt_{fs} \times 10^{-15}
\]
\[
E_\text{in} = \sum_k |A(t_k)|^2 \, dt_s \quad [J]
\]

### Step 2 — input average power
\[
P_{\text{in,avg}} = E_\text{in} \, f_\text{rep} \quad [W]
\]

### Step 3 — required net gain ratio
\[
G_\text{net} = \frac{P_{\text{out,target}}}{P_{\text{in,avg}}}
\]

### Step 4 — convert to effective loss in dB/m
Solve:
\[
G_\text{net} = 10^{-\text{loss_eff}\,L/10}
\Rightarrow
\boxed{
\text{loss_eff_db_per_m} = -\frac{10}{L}\log_{10}(G_\text{net})
}
\]

### Step 5 — total loss passed to backend
\[
\boxed{
\text{loss_total_db_per_m} = \text{loss_intrinsic_db_per_m} + \text{loss_eff_db_per_m}
}
\]

fiber_amp_wrap builds a temporary `FiberCfg` where:
- `physics.loss_db_per_m = loss_total_db_per_m`
and then calls `FiberStage.process(...)`.

---

## 4) Guardrails (fail loudly)

fiber_amp_wrap must raise ValueError if:
- rep_rate_mhz missing or <= 0
- power_out_w <= 0
- L <= 0
- P_in_avg <= 0 (pulse window empty, normalization wrong, etc.)
- G_net <= 0

Optional (project choice): reject absurd gain requests (e.g. > 80 dB total) to prevent numeric blowups.

---

## 5) Testing contract

### Unit tests (no external backends)
- Stub/monkeypatch FiberStage so it applies the analytic gain/loss scaling:
  \[
  P_\text{out}/P_\text{in} = 10^{-\text{loss_total}\,L/10}
  \]
- Verify the wrapper hits `power_out_w` exactly within tolerance.

### Optional integration tests (if gnlse installed)
- Run FiberStage backend normally (e.g. wust_gnlse)
- With gamma=0 and dispersion ~ 0, verify the measured output average power matches target.

---

## 6) What NOT to do
- Do not replace distributed gain with a single lumped multiplier after propagation.
  That changes \(\int \gamma P(z)\,dz\) and breaks SPM physics.
