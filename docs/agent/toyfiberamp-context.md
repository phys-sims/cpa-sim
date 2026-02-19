# ToyFiberAmp / ToyAmp: specify **measurement-plane average output power** (`amp_power_w`) instead of `gain_db`
*(agent context + ADR-ready notes)*

This document defines a lab-friendly control for the **toy fiber amplifier** stage used in `cpa-sim`:

- **`amp_power_w`** — **average output power at the measurement plane**, in Watts.

The stage then computes the **distributed gain** needed to hit that average power, while preserving
the physics that matters for CPA (dispersion + Kerr SPM happening *along* the fiber).

This doc supersedes the older “set `gain_db` directly” guidance.

**Source being clarified/replaced:** `toyamp_amp_power_w_agent_context.md`. fileciteturn1file0
**ADR template:** `_template-full.md`. fileciteturn1file1

---

## 0) Scope and non-goals

### In scope
- A **single knob** for experiments/scripts: `amp_power_w` (W), defined at the **measurement plane**.
- Centralized mapping inside the stage:
  - `amp_power_w` + `rep_rate_mhz` + incoming pulse energy → required net power gain.
  - Required net power gain → **distributed gain** parameterization for the backend.
- Compatibility with two backends:
  1) Current in-repo SSFM toy implementation (`ToyFiberAmpStage`)
  2) Future/alternate backend: WUST-FOG python GNLSE

### Not in scope (v1)
- EDFA physics (rate equations, saturation, ASE).
- Modeling connectors/isolators/couplers as separate elements.
  - **Assumption for v1:** measurement plane is the stage output plane.

---

## 1) Definitions and conventions (do not skip)

### Measurement plane
- **`amp_power_w` is defined at the measurement plane.**
- Because v1 does not model connectors/isolators/etc., the **measurement plane == stage output**.

If later a real setup reports power after extra optics, either:
- (preferred) add explicit loss stages, or
- (optional) add a single `post_amp_loss_db` parameter and document the plane shift.

### Repetition rate
To map between average power and per-pulse energy, repetition rate is required:

\[
E_\text{pulse} = \frac{P_\text{avg}}{f_\text{rep}},
\qquad f_\text{rep} = (\text{rep\_rate\_mhz})\times 10^6
\]

**Schema requirement:** `PulseSpec.rep_rate_mhz: float` (MHz, must be > 0).

### Field normalization (critical)
The mapping is physically meaningful only if the simulator uses:
- \(|A(t)|^2\) = **instantaneous power** in Watts
- `dt` is in seconds
Then:
\[
E_\text{pulse} = \int |A(t)|^2\,dt
\]
is in Joules, and `P_avg = E_pulse * f_rep` is in Watts.

If the codebase uses normalized units, `amp_power_w` becomes a *convenience scale factor* rather than a true watt value.
A human must confirm normalization conventions before claiming physical units.

---

## 2) Backend loss/gain conventions

### 2.1 WUST-FOG convention (confirmed from source)
WUST-FOG uses a frequency-domain linear operator:
\[
L(\omega)= iB(\omega) - \frac{\alpha}{2}
\]
and computes:
\[
\alpha = \ln\left(10^{\text{loss}/10}\right)
\]
where `loss` is in **dB/m**.

That implies power evolution:
\[
P(z)=P(0)\,10^{-\text{loss}\,z/10}
\]

So:
- `loss > 0` → attenuation
- `loss < 0` → **distributed gain** (power growth)

**Key takeaway:** with WUST-FOG, *gain is implemented by making `loss` negative*.

### 2.2 Current in-repo ToyFiberAmpStage convention (code-grounded)
Current config:
- `gain_db`: **total power gain across the fiber length** (dB)
- `loss_db_per_m`: power loss **per meter** (dB/m)

Net power ratio across length \(L\) is:
\[
\frac{P_\text{out}}{P_\text{in}}
=
10^{\text{gain\_db}/10}
\cdot
10^{-\text{loss\_db\_per\_m}\,L/10}
\]

---

## 3) Config/API changes (target end state)

### 3.1 Add repetition rate to pulse spec
Add to `PulseSpec`:
- `rep_rate_mhz: float` (required, > 0)

### 3.2 Replace user-facing `gain_db` knob with `amp_power_w`
For a lab-facing amplifier stage config (name may remain `ToyFiberAmpCfg`):

- `amp_power_w: float` — **average output power at the measurement plane** (W)
- Keep physical fiber params:
  - `length_m`, `beta2_s2_per_m`, `gamma_w_inv_m`, `n_steps`
- Keep optional *intrinsic* loss:
  - `loss_db_per_m: float = 0.0`
- `gain_db` becomes **internal/derived** (computed at runtime), not required in configs.

**Backward compatibility (optional transition):**
- allow exactly one of `gain_db` or `amp_power_w`, with `gain_db` deprecated.

---

## 4) Runtime mapping: `amp_power_w` → distributed gain

### Step 1 — Compute incoming pulse energy (shape-agnostic)
Given `field_t` samples and `dt`:

\[
E_\text{in} = \sum |A(t_k)|^2\,\Delta t
\]

### Step 2 — Convert to incoming average power
\[
P_{\text{in,avg}} = E_\text{in}\,f_\text{rep}
\]

### Step 3 — Required net power ratio at the measurement plane
Because measurement plane == stage output in v1:

\[
G_\text{net} = \frac{P_{\text{out,target}}}{P_{\text{in,avg}}}
= \frac{\text{amp\_power\_w}}{P_{\text{in,avg}}}
\]

### Step 4a — If using current ToyFiberAmpStage parameterization (`gain_db` + `loss_db_per_m`)
Solve for the `gain_db` that produces the desired **net** ratio:

\[
G_\text{net}
=
10^{\text{gain\_db}/10}
\cdot
10^{-\text{loss\_db\_per\_m}\,L/10}
\]

\[
\Rightarrow\quad
\boxed{\text{gain\_db} = 10\log_{10}(G_\text{net}) + (\text{loss\_db\_per\_m}\cdot L)}
\]

So the stage can:
1) compute `gain_db_required` from `amp_power_w`
2) run the existing SSFM code unchanged using that derived `gain_db_required`.

### Step 4b — If using WUST-FOG (`loss` only, dB/m; negative loss = gain)
WUST-FOG collapses loss+gain into one net dB/m parameter:

\[
\frac{P_\text{out}}{P_\text{in}} = 10^{-\text{loss}\,L/10}
\]

So:
\[
\boxed{\text{loss} = -\frac{10}{L}\log_{10}(G_\text{net})}
\qquad [\text{dB/m}]
\]

---

## 5) Guardrails (prevent silent nonsense)

- Validate:
  - `rep_rate_mhz > 0`
  - `amp_power_w > 0`
  - `E_in > 0` and `P_in_avg > 0`
- If `P_in_avg` is extremely small, fail loudly with a message that points to:
  - missing rep rate
  - wrong field normalization
  - pulse window not containing a pulse
- Clamp maximum requested `G_net` (project choice). Exponential gain can explode numerically.
- Optional one-step correction loop (useful if normalization is imperfect):
  1) run once with computed gain
  2) measure achieved `P_out_avg`
  3) update using:
     \[
     \text{gain\_db} \leftarrow \text{gain\_db} + 10\log_{10}\left(\frac{P_{\text{out,target}}}{P_{\text{out,meas}}}\right)
     \]
  4) rerun

---

## 6) Implementation notes (agent-facing)

### Where the mapping should live
- Inside the amplifier stage implementation (`ToyFiberAmpStage` or the WUST-FOG wrapper stage).
- External scripts should only set `amp_power_w` and `rep_rate_mhz`.

### Minimal pseudocode
```python
E_in = sum(abs(A_t)**2) * dt
P_in_avg = E_in * f_rep_hz
G_net = amp_power_w / P_in_avg

# Current toy backend:
gain_db = 10*log10(G_net) + loss_db_per_m*length_m

# WUST backend:
loss_eff_db_per_m = -(10/length_m) * log10(G_net)
```

### What not to do
- Do not “apply gain” as a single amplitude multiplier and skip distributed propagation.
  That breaks SPM physics because \(\int \gamma P(z) dz\) changes.

---

## 7) Tests (contract + physics)

### Contract tests (must pass)
1) **Hits target average power (measurement plane)**
   - Construct a pulse with known `E_in` under the simulator’s normalization.
   - Set `rep_rate_mhz`, `amp_power_w`.
   - Run stage.
   - Compute achieved `P_out_avg = E_out * f_rep`.
   - Assert close to `amp_power_w` within tolerance.

2) **Loss compensation correctness**
   - Set `loss_db_per_m > 0`.
   - Confirm computed `gain_db` includes `loss_db_per_m*L` term and still hits target.

### Physics sanity tests (should pass, but accept small numerical drift)
3) **SPM monotonicity**
   - With `gamma_w_inv_m > 0`, sweep `amp_power_w` upward.
   - Bandwidth should monotonically increase (or at least not decrease) beyond numerical noise.

4) **Distributed vs lumped regression guard**
   - Compare distributed gain fiber vs (lumped multiplier + passive fiber) and assert they differ when `gamma>0`.
   - Prevents accidental “optimization” that deletes distributed gain.

---

## 8) Agent vs human responsibilities

### Safe for an agent
- Add `rep_rate_mhz` to schema and thread through constructors/tests.
- Add `amp_power_w` to config and implement the mapping logic above.
- Update examples/docs/tests to use `amp_power_w`.
- Implement contract tests.

### Needs human supervision
- Confirm \(|A|^2\) and `dt` units so `amp_power_w` is physically meaningful.
- Decide numeric clamp thresholds for `G_net`.
- Validate end-to-end “no SPM vs visible SPM” demo aligns with expected plots.

---

# ADR drafting context (fill into `_template-full.md`)

Below is ADR-ready content tailored to the template. Copy/paste into a new ADR file.

## Title
**Expose amplifier control as measurement-plane average power (`amp_power_w`)**

## Suggested metadata
- **ADR ID:** (next available)
- **Status:** Proposed
- **Date:** 2026-02-19
- **Deciders:** (add)
- **Area:** cpa-sim
- **Tags:** api, data-model, physics, testing

## Context (problem statement)
- Current configs require `gain_db`, which is not a lab knob and is easy to misuse due to:
  - field-vs-power gain confusion
  - missing/implicit repetition rate
  - duplicated conversion code in scripts
- For CPA/SPM studies at high rep rates, the most stable “lab-facing” scalar is **measured average power**.
- v1 will not model post-amp optics, so “measurement plane” is the amplifier output.

## Options considered

**Option A — Keep `gain_db` as user knob**
- Pros: simplest code, matches current implementation
- Cons:
  - not a lab knob
  - repeated mapping code in scripts
  - easy to mis-handle gain conventions and rep rate
- Risks: wrong power scaling silently invalidates SPM/CPA conclusions

**Option B — User sets `amp_power_w` at measurement plane; stage derives distributed gain (recommended)**
- Pros:
  - configs match how experiments are specified and compared
  - mapping centralized; fewer A/B script bugs
  - preserves distributed gain so SPM physics remains meaningful
- Cons:
  - requires `rep_rate_mhz` to be threaded through the data model
  - requires clear unit conventions for \(|A|^2\) and `dt`
- Risks:
  - if normalization is not physical, “W” is only a relative scale (mitigate with docs/tests)

**Option C — Expose “pump power” knob (e.g., PriTel pump watts)**
- Pros: matches a hardware UI control
- Cons:
  - not portable across models
  - requires a calibration layer pump→signal output and likely saturation/ASE modeling to be honest
  - adds bloat and can still be wrong without lab characterization
- Recommendation: defer; optionally add later as a calibrated wrapper around Option B.

## Decision (recommended)
Choose **Option B** for v1. Keep Option C as a possible future extension via calibration.

## Consequences
- Positive:
  - simpler, safer experiment configs
  - consistent comparisons between simulations and measured power settings
- Negative / mitigations:
  - requires rep-rate in pulse spec → update all constructors/tests
  - must document unit conventions; add contract tests and debug logging
- Migration plan:
  - add `rep_rate_mhz` (required)
  - add `amp_power_w`, deprecate `gain_db`
  - update examples/tests
- Test strategy:
  - “hits target Pavg” contract test
  - loss compensation test
  - SPM monotonicity sanity
- Monitoring/telemetry:
  - debug log `E_in`, `P_in_avg`, `G_net`, derived `gain_db`/`loss_eff`, achieved `P_out_avg`

## Open questions
- Should `amp_power_w` be interpreted as true Watts (requires unit enforcement) or “simulation watts” (relative)?
- Clamp policy for extreme `G_net`?
- Should the WUST-FOG backend be the default for this stage, or remain optional?

---

## Changelog
- 2026-02-19 — Proposed (drafted)
