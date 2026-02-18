# Toy fiber amp A vs B gallery (PNG-friendly)

Use this page to present side-by-side figures for **case A (direct)** vs **case B (CPA)** with identical explicit laser generation settings.

## Run once to generate artifacts

```bash
python scripts/examples/toy_amp_case_ab_compare.py --out artifacts/toy-amp-case-ab --emit-plots
```

This writes:
- `artifacts/toy-amp-case-ab/comparison_summary.json`
- `artifacts/toy-amp-case-ab/case-a/run_summary.json`
- `artifacts/toy-amp-case-ab/case-b/run_summary.json`
- stage SVG plots under each case's `stage-plots/`

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
