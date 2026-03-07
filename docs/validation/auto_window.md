# AutoWindow (free-space phase-only backends)

AutoWindow is a runtime policy for reducing **time-domain wraparound artifacts** in the current free-space, phase-only stages.

## What AutoWindow does

When enabled for a stage, AutoWindow:

1. Runs the stage normally.
2. Measures **edge-energy fraction** in the output temporal intensity.
3. If edge energy is above threshold, increases the time window by **zero-padding in time** (while keeping `dt` fixed), reruns the stage, and repeats until clean or limits are reached.

This is implemented as iterative reruns in `run_with_auto_window(...)` and currently used by free-space phase-only stage backends.

## What AutoWindow does **not** do

AutoWindow is not a universal sampling fix.

- It **does not fix Nyquist aliasing** caused by `dt` being too large (insufficient sample rate / frequency span).
- It **does not recover lost information** when insufficient bandwidth was already represented on the grid.

If Nyquist-guard energy is already too high on input, AutoWindow raises an error instead of masking the issue.

## Policy keys and defaults

These policy keys control behavior:

- `cpa.auto_window.enabled` (default: `False`)
- `cpa.auto_window.stages` (default: unset; if unset and enabled, all stage names are eligible)
- `cpa.auto_window.print` (default: `False`)
- `cpa.auto_window.edge_fraction` (default: `0.05`)
- `cpa.auto_window.max_edge_energy_fraction` (default: `1e-6`)
- `cpa.auto_window.max_iters` (default: `6`)
- `cpa.auto_window.growth_factor` (default: `2.0`)
- `cpa.auto_window.prefer_pow2` (default: `True`)
- `cpa.auto_window.max_n_samples` (default: `None`)
- `cpa.auto_window.recenter_each_iter` (default: `True`)
- `cpa.auto_window.nyquist_guard_fraction` (default: `0.05`)
- `cpa.auto_window.max_nyquist_energy_fraction` (default: `1e-6`)

Example policy dictionary:

```python
policy = {
    "cpa.auto_window.enabled": True,
    "cpa.auto_window.stages": ["stretcher", "compressor"],
    "cpa.auto_window.print": True,
    "cpa.auto_window.max_edge_energy_fraction": 1e-7,
}
```

## Provenance and metrics

AutoWindow emits run metadata in two places:

- `state.meta["auto_window_events"]`: per-attempt event records (stage, attempt index, `n_samples`, edge-energy values, thresholds, etc.).
- Per-stage metrics include `auto_window_*` fields such as attempts, reruns, input/output sample counts, and final edge-energy fraction.

## CLI usage

Enable with CLI policy flags:

```bash
cpa-sim run configs/examples/basic_cpa.yaml --out out/basic --auto-window --auto-window-print
```

Optional stage scoping via comma-separated names:

```bash
cpa-sim run configs/examples/basic_cpa.yaml --out out/basic --auto-window --auto-window-stages stretcher,compressor
```

## Note on future backends

Current AutoWindow reruns are intended for **phase-only free-space backends**.

Future free-space backends that are dispersion-aware ray-tracing or spatial propagation models may be significantly more expensive; for those, auto-reruns should likely be disabled by default (or require explicit opt-in) to avoid surprising runtime costs.
