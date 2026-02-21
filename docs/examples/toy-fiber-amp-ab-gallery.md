# Toy fiber amp A vs B gallery (PNG-friendly)

Use this page to present side-by-side figures for **case A (direct)** vs **case B (CPA)** with identical explicit laser generation settings.

## Run once to generate artifacts

```bash
python -m cpa_sim.examples.toy_amp_case_ab_compare --out artifacts/toy-amp-case-ab --emit-plots
```

This writes:
- `artifacts/toy-amp-case-ab/comparison_summary.json`
- `artifacts/toy-amp-case-ab/case-a/run_summary.json`
- `artifacts/toy-amp-case-ab/case-b/run_summary.json`
- stage SVG plots under each case's `stage-plots/`

## Sampling policy for short pulses

The toy A/B scripts now enforce a pulse-grid policy before running the pipeline:

- temporal sampling must satisfy `dt_fs <= width_fs / N_min` (default `N_min=24`, i.e. 20–40+ points across FWHM),
- optional FFT safety checks verify both a minimum time-window-to-FWHM ratio and a Nyquist spectral margin tied to pulse shape (`gaussian` or `sech2`).

This guardrail prevents under-resolved short pulses from producing misleading peak power and spectral broadening metrics in the gallery outputs.
If a config violates policy, examples raise early with a clear error; for exploratory use, the same helper can emit warnings in non-strict mode.

## Optional: convert SVG stage plots to PNG

If you want PNG files for slides/docs:

```bash
# Example with ImageMagick (if installed)
magick artifacts/toy-amp-case-ab/case-a/stage-plots/toy_amp_time_intensity.svg \
  artifacts/toy-amp-case-ab/case-a/stage-plots/toy_amp_time_intensity.png
```

## Embed PNGs side by side

| Case A (direct) | Case B (CPA) |
| --- | --- |
| ![Case A toy amp time intensity](../../artifacts/toy-amp-case-ab/case-a/stage-plots/toy_amp_time_intensity.png) | ![Case B toy amp time intensity](../../artifacts/toy-amp-case-ab/case-b/stage-plots/toy_amp_time_intensity.png) |
| ![Case A toy amp spectrum](../../artifacts/toy-amp-case-ab/case-a/stage-plots/toy_amp_spectrum.png) | ![Case B toy amp spectrum](../../artifacts/toy-amp-case-ab/case-b/stage-plots/toy_amp_spectrum.png) |

## Notes

- Both cases use explicit `LaserGenCfg` setup (same pulse/beam spec) so the only difference is chain topology.
- Use `comparison_summary.json` to quote numeric side-by-side metrics.
- The shared toy amp gain is hardwired in `src/cpa_sim/examples/toy_amp_case_ab_compare.py` and reused by both case A and case B.
