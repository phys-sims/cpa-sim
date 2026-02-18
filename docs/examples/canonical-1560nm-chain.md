# Canonical 1560 nm CPA chain example

This guide shows how to run the canonical 1560 nm CPA chain example and publish stage outputs as embedded PNG images in your documentation.

> Note: the stage-plot policy in `cpa-sim` emits SVG files by default. This doc includes a simple SVG→PNG conversion step so you can upload PNGs to docs/Wiki systems.

## What this example does

The script `scripts/examples/canonical_1560nm_chain.py` builds and runs a deterministic CPA chain with explicit stage ordering:

1. **Fiber prechirp**: DCF-like `FiberCfg` at **1560 nm** with anomalous dispersion sign convention (`beta2 < 0`)
2. **Amplification**: EDFA-like gain using current `simple_gain` (`AmpCfg`)
3. **Compressor**: `TreacyGratingPairCfg` (`treacy_compressor`) as phase action

Pipeline policy enables per-stage plots:

- `cpa.emit_stage_plots = True`
- `cpa.stage_plot_dir = <your plot dir>`

The script writes `run_summary.json` with metrics and an artifact index.

## 1) Run the example

From repo root:

```bash
python scripts/examples/canonical_1560nm_chain.py \
  --ci-safe \
  --out artifacts/canonical-1560nm-chain-ci \
  --plot-dir artifacts/canonical-1560nm-chain-ci/plots
```

Use `--ci-safe` for tiny-grid runtime suitable for CI/docs workflows.

For a larger run:

```bash
python scripts/examples/canonical_1560nm_chain.py \
  --out artifacts/canonical-1560nm-chain \
  --plot-dir artifacts/canonical-1560nm-chain/stage-plots \
  --seed 1560
```


## Treacy compressor debug/probe script

To debug compressor behavior directly, use `scripts/examples/treacy_compressor_probe.py`.
This script scans Treacy grating separation while keeping the 1560 nm DCF prechirp path fixed, and writes:

- `probe_summary.json` (full scan + best point)
- `probe_results.csv` (quick spreadsheet/plot input)

Example:

```bash
python scripts/examples/treacy_compressor_probe.py \
  --ci-safe \
  --out artifacts/treacy-compressor-probe-ci \
  --start-um 60000 \
  --stop-um 180000 \
  --step-um 5000
```

## 2) Inspect generated artifacts

You should see:

- `artifacts/.../run_summary.json`
- per-stage SVG files in your `--plot-dir`, e.g.
  - `laser_init_time_intensity.svg`
  - `fiber_dcf_1560nm_time_intensity.svg`
  - `edfa_like_gain_time_intensity.svg`
  - `treacy_compressor_time_intensity.svg`
  - `metrics_time_intensity.svg`

## 3) Convert SVG stage plots to PNG

### Option A: Python (recommended, deterministic)

Install converter once:

```bash
python -m pip install cairosvg
```

Convert all stage SVGs to PNG files:

```bash
python - <<'PY'
from pathlib import Path
import cairosvg

plot_dir = Path("artifacts/canonical-1560nm-chain-ci/plots")
for svg_path in sorted(plot_dir.glob("*.svg")):
    png_path = svg_path.with_suffix(".png")
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=180)
    print(f"wrote {png_path}")
PY
```

### Option B: ImageMagick

If your environment has ImageMagick:

```bash
magick mogrify -format png artifacts/canonical-1560nm-chain-ci/plots/*.svg
```

## 4) Upload PNGs into your doc system

`codex` can generate files locally, but it cannot directly upload images into your external docs platform.

Use your normal docs UI/CLI to upload the generated PNGs from:

- `artifacts/canonical-1560nm-chain-ci/plots/*.png`

Typical flow:

1. Open your docs/Wiki editor.
2. Upload selected PNGs (drag/drop or media upload).
3. Copy returned hosted URLs (or repo-relative paths if using git-backed docs).
4. Embed them in markdown.

## 5) Embed PNGs in markdown

Example markdown section for your report:

```md
## Canonical 1560 nm chain outputs

### Fiber stage (time intensity)
![Fiber stage time intensity](images/fiber_dcf_1560nm_time_intensity.png)

### Fiber stage (spectrum)
![Fiber stage spectrum](images/fiber_dcf_1560nm_spectrum.png)

### Compressor stage (time intensity)
![Compressor stage time intensity](images/treacy_compressor_time_intensity.png)
```

If your system returns absolute hosted URLs, use those directly instead of `images/...`.

## 6) Suggested doc structure (copy/paste template)

```md
# Canonical 1560 nm CPA example

## Purpose
- Why this chain is representative.

## Configuration summary
- Seed
- Grid mode (`--ci-safe` vs full)
- Stage ordering

## Results
- Key metrics from `run_summary.json`
- Embedded PNGs per stage

## Reproducibility
- Exact command used
- Commit SHA
- Artifact directory
```

This keeps your documentation reproducible and easy to audit.
