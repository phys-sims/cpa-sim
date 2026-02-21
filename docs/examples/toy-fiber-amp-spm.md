# Toy fiber amp SPM examples (A/B)

## Scope and limitations

This backend (`kind: toy_fiber_amp`) is a deterministic teaching/CI model, not a full EDFA model.

It includes only:
- stage-derived distributed gain from target average output power (`amp_power_w`),
- optional distributed passive loss (`loss_db_per_m`),
- second-order dispersion (`beta2_s2_per_m`),
- Kerr SPM (`gamma_w_inv_m`) via split-step propagation.

It does **not** include ASE, pump depletion, or wavelength-dependent gain.

## Matching criterion used in examples

Both examples use **measurement-plane average power matching** (same `amp_power_w` and physical length settings).
Comparisons of nonlinear distortion are interpreted with that criterion.

## Example A: direct seed -> toy amp

Run:

```bash
python scripts/examples/toy_amp_case_a_direct.py --out artifacts/toy-amp-case-a --emit-plots
```

Expected qualitative behavior:
- strong SPM from high peak power at amp input,
- spectral broadening relative to a `gamma=0` run,
- higher B-integral proxy.

## Example B: CPA-style seed -> stretcher -> toy amp -> Treacy compressor

Run:

```bash
python scripts/examples/toy_amp_case_b_cpa.py --out artifacts/toy-amp-case-b --emit-plots
```

Expected qualitative behavior:
- stretched pulse enters the amp with reduced peak power,
- reduced B-integral proxy during amplification vs Example A,
- after compression, pulse remains amplified but with less nonlinear distortion than direct amplification.


## Combined runner (A vs B side-by-side)

Run both cases in one command and emit a comparison summary:

```bash
python scripts/examples/toy_amp_case_ab_compare.py --out artifacts/toy-amp-case-ab --emit-plots
```

This writes per-case summaries plus `comparison_summary.json` with the same key metrics for direct side-by-side review.

## Notes on metrics

`toy_fiber_amp` emits stage metrics:
- energy in/out (`energy_in_au`, `energy_out_au`) and average power in/out (`power_in_avg_w`, `power_out_avg_w`),
- peak power in/out (`peak_power_in_w`, `peak_power_out_w`),
- RMS spectral bandwidth in/out (`bandwidth_in_rad_per_fs`, `bandwidth_out_rad_per_fs`),
- B-integral proxy (`b_integral_proxy_rad = gamma * L * peak_power_in_w`).

The B-integral value is a proxy and should be interpreted qualitatively.
