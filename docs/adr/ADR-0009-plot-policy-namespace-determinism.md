**Title:** Plot policy namespace, default windowing/normalization, and determinism expectations.

- **ADR ID:** ADR-0009
- **Status:** Accepted
- **Date:** 2026-03-06
- **Deciders:** @cpa-sim maintainers
- **Area:** plotting-policy
- **Related ADRs:** ADR-0001, ADR-0003, ADR-0008
- **Tags:** plotting, policy, determinism, validation
- **Scope:** cpa-sim

### Context
`cpa-sim` now has reusable plotting helpers for stage line plots and dispersive-wave heatmaps. We need one stable policy namespace for plot behavior so users can tune windows/scales without touching stage implementations, while keeping default behavior deterministic and testable.

### Decision

#### 1) Canonical plot policy namespace
All run-level plotting controls live under the `cpa.plot.*` key space in a flat policy bag.

- Line window controls:
  - `cpa.plot.line.threshold_fraction`
  - `cpa.plot.line.min_support_width`
  - `cpa.plot.line.pad_fraction`
- Heatmap x-window controls:
  - `cpa.plot.heatmap.coverage_quantile`
  - `cpa.plot.heatmap.pad_fraction`
  - `cpa.plot.heatmap.fallback_behavior` (`full_axis` or `line_window`)
- Heatmap normalization controls:
  - `cpa.plot.heatmap.scale` (`linear` or `log`)
  - `cpa.plot.heatmap.vmin_percentile`
  - `cpa.plot.heatmap.vmax_percentile`
  - `cpa.plot.heatmap.dynamic_range_db`
  - `cpa.plot.heatmap.gamma`

Operational keys outside the namespace remain:
- `cpa.emit_stage_plots`
- `cpa.stage_plot_dir`

#### 2) Default windowing and normalization behavior
Defaults are intentionally conservative and deterministic:

- Line window defaults:
  - threshold fraction: `1e-3`
  - minimum support width: `0.0`
  - pad fraction: `0.05`
- Heatmap x-window defaults:
  - coverage quantile: `0.999`
  - pad fraction: `0.10`
  - fallback behavior: `full_axis`
- Heatmap normalization defaults:
  - scale: `linear`
  - vmin percentile: `0.0`
  - vmax percentile: `99.9`
  - log dynamic range floor: `60 dB` (used when scale is `log`)
  - gamma: `1.0` (identity)

Defaults are applied by policy readers; if a key is absent, default behavior must be identical across runs for the same numeric inputs.

#### 3) Determinism expectations for bounds and normalization
For identical arrays and policy values:

- Returned line x-limits are deterministic.
- Returned heatmap x-limits are deterministic (quantile interpolation and padding are pure functions of data/policy).
- Resolved heatmap `(vmin, vmax)` and transformed/clipped arrays are deterministic.
- Log scaling floor and resulting `LogNorm` bounds are deterministic.

No plotting helper may sample randomness or inspect external state (clock, locale, env) when calculating bounds/norms.

#### 4) Validation tiers and pinned tests
Behavior is pinned across tiers:

- **Unit (`unit`)**
  - `tests/unit/test_plot_window_policy.py`
  - `tests/unit/test_plot_window_autoscale.py`
  - `tests/unit/test_plotting_autoscale.py`
  - `tests/unit/test_plotting_dispersive_wave.py`
- **Integration (`integration`)**
  - `tests/integration/test_example_plot_artifacts.py`
  - `tests/integration/test_wust_gnlse_example_script.py`
  - `tests/integration/test_spm_after_fiber_amp_example.py`
- **Physics (`physics`, optionally `slow`)**
  - `tests/physics/test_fiber_dispersive_wave.py`
  - `tests/physics/test_fiber_dispersive_wave_plots.py`

Any change to key names, defaults, or deterministic bound/norm rules requires:
1. ADR update,
2. updates to relevant pinned tests,
3. `STATUS.md` update when behavior or validation outcomes change.

### Consequences
- **Positive:** users can override plot behavior from policy/CLI wrappers without stage code edits.
- **Positive:** one stable namespace supports all stage backends and docs workflows.
- **Tradeoff:** more policy keys increase documentation burden; examples must stay synchronized.

### Validation
- Unit tests verify policy parsing and autoscale behavior.
- Integration tests verify example artifacts and policy-driven plotting paths.
- Physics tests verify dispersive-wave outputs remain scientifically meaningful when policy-controlled plotting is applied.
