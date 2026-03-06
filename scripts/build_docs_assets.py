from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

LIGHT_SPEED_M_PER_S = 299_792_458.0
EPS = 1e-30
DEFAULT_OUTPUT_DIR = Path("docs/assets/generated/gnlse-dispersive-wave")
DOCS_RENDER_ROOT = "docs_rendering"
DOCS_RUNTIME_STAGE_PLOTS = "runtime_stage_plots"
SVG_NAMES = (
    "spectrum_z0_vs_zL.svg",
    "evolution_wavelength_vs_distance.svg",
    "evolution_delay_vs_distance.svg",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build generated SVG assets for docs examples.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--mode",
        choices=["ultra-fast", "ci", "full"],
        default="ci",
        help="Asset generation mode. 'ultra-fast' is suitable for PR docs builds.",
    )
    parser.add_argument(
        "--allow-missing-gnlse",
        action="store_true",
        help=(
            "If optional plotting/gnlse dependencies are unavailable, "
            "write deterministic placeholder SVGs instead of failing."
        ),
    )
    return parser


def _downsample_axis(data: np.ndarray, max_points: int, axis: int) -> np.ndarray:
    if data.shape[axis] <= max_points:
        return data
    idx = np.linspace(0, data.shape[axis] - 1, max_points, dtype=int)
    return np.take(data, idx, axis=axis)


def _to_wavelength_nm(w_rad_per_fs: np.ndarray, center_wavelength_nm: float) -> np.ndarray:
    omega0_rad_per_s = 2.0 * np.pi * LIGHT_SPEED_M_PER_S / (center_wavelength_nm * 1e-9)
    omega_abs_rad_per_s = omega0_rad_per_s + (w_rad_per_fs * 1e15)

    lam_nm = np.full_like(omega_abs_rad_per_s, np.nan, dtype=float)
    valid = omega_abs_rad_per_s > 0.0
    lam_nm[valid] = 2.0 * np.pi * LIGHT_SPEED_M_PER_S / omega_abs_rad_per_s[valid] * 1e9
    return lam_nm


def _load_z_traces(npz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(npz_path) as data:
        z_m = np.asarray(data["z_m"], dtype=float)
        t_fs = np.asarray(data["t_fs"], dtype=float)
        w_rad_per_fs = np.asarray(data["w_rad_per_fs"], dtype=float)
        at = np.asarray(data["at_zt_real"], dtype=float) + 1j * np.asarray(
            data["at_zt_imag"], dtype=float
        )
    return z_m, t_fs, w_rad_per_fs, at


def _normalize_svg_whitespace(svg_path: Path) -> None:
    lines = svg_path.read_text(encoding="utf-8").splitlines()
    normalized = "\n".join(line.rstrip() for line in lines) + "\n"
    svg_path.write_text(normalized, encoding="utf-8")


def _load_pyplot() -> tuple[Any, Any]:
    try:
        import matplotlib
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runner image
        raise RuntimeError(
            "matplotlib is required to render docs assets; install docs dependencies "
            "or use --allow-missing-gnlse for placeholder SVGs"
        ) from exc

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return matplotlib, plt


def _save_placeholder_svgs(outdir: Path, reason: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    escaped = reason.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">',
        '  <rect width="100%" height="100%" fill="#0f172a"/>',
        '  <text x="60" y="160" fill="#e2e8f0" font-size="34" font-family="sans-serif">Docs asset unavailable in this build</text>',
        f'  <text x="60" y="230" fill="#93c5fd" font-size="24" font-family="monospace">{escaped}</text>',
        "</svg>",
    ]
    for name in SVG_NAMES:
        output = outdir / name
        output.write_text("\n".join(body) + "\n", encoding="utf-8")


def _build_svgs(
    *,
    z_m: np.ndarray,
    t_fs: np.ndarray,
    w_rad_per_fs: np.ndarray,
    at_zt: np.ndarray,
    outdir: Path,
) -> None:
    _, plt = _load_pyplot()
    outdir.mkdir(parents=True, exist_ok=True)

    wavelength_nm = _to_wavelength_nm(w_rad_per_fs, center_wavelength_nm=835.0)
    aw_zt = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(at_zt, axes=1), axis=1), axes=1)

    power_t = np.abs(at_zt) ** 2
    power_w = np.abs(aw_zt) ** 2

    max_columns = 900
    max_rows = 120

    z_small = _downsample_axis(z_m, max_rows, axis=0)
    t_small = _downsample_axis(t_fs, max_columns, axis=0)
    wavelength_small = _downsample_axis(wavelength_nm, max_columns, axis=0)
    power_t_small = _downsample_axis(
        _downsample_axis(power_t, max_rows, axis=0), max_columns, axis=1
    )
    power_w_small = _downsample_axis(
        _downsample_axis(power_w, max_rows, axis=0), max_columns, axis=1
    )

    plt.rcParams.update(
        {
            "axes.grid": True,
            "grid.alpha": 0.25,
            "font.size": 11,
            "svg.hashsalt": "cpa-sim-docs-assets-v1",
        }
    )

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(wavelength_nm, np.log10(power_w[0] + EPS), label="z = 0")
    ax.plot(wavelength_nm, np.log10(power_w[-1] + EPS), label=f"z = {z_m[-1]:.3f} m")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel(r"$\log_{10}(P_\lambda)$ [a.u.]")
    ax.set_title("Dispersive-wave spectrum evolution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / SVG_NAMES[0],
        format="svg",
        metadata={"Date": "1970-01-01T00:00:00", "Creator": "cpa-sim docs asset builder"},
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    m = ax.imshow(
        np.log10(power_w_small + EPS),
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=[
            float(np.nanmin(wavelength_small)),
            float(np.nanmax(wavelength_small)),
            float(z_small[0]),
            float(z_small[-1]),
        ],
        interpolation="nearest",
        rasterized=True,
    )
    fig.colorbar(m, ax=ax, label=r"$\log_{10}(P_\lambda)$ [a.u.]")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Wavelength vs distance")
    fig.tight_layout()
    fig.savefig(
        outdir / SVG_NAMES[1],
        format="svg",
        metadata={"Date": "1970-01-01T00:00:00", "Creator": "cpa-sim docs asset builder"},
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    m = ax.imshow(
        np.log10(power_t_small + EPS),
        origin="lower",
        aspect="auto",
        cmap="magma",
        extent=[float(t_small[0]), float(t_small[-1]), float(z_small[0]), float(z_small[-1])],
        interpolation="nearest",
        rasterized=True,
    )
    fig.colorbar(m, ax=ax, label=r"$\log_{10}(|A(t,z)|^2)$ [a.u.]")
    ax.set_xlabel("Delay (fs)")
    ax.set_ylabel("Distance (m)")
    ax.set_title("Delay vs distance")
    fig.tight_layout()
    fig.savefig(
        outdir / SVG_NAMES[2],
        format="svg",
        metadata={"Date": "1970-01-01T00:00:00", "Creator": "cpa-sim docs asset builder"},
    )
    plt.close(fig)

    for name in SVG_NAMES:
        _normalize_svg_whitespace(outdir / name)


def _cleanup_run_dir(run_dir: Path) -> None:
    if run_dir.exists():
        for child in run_dir.iterdir():
            if child.is_file():
                child.unlink()
        run_dir.rmdir()


def main() -> None:
    args = _build_parser().parse_args()
    outdir = args.outdir
    # Docs-only rendering path: isolate temporary runtime stage artifacts from published docs SVGs.
    run_dir = outdir / DOCS_RENDER_ROOT / DOCS_RUNTIME_STAGE_PLOTS
    run_dir.mkdir(parents=True, exist_ok=True)

    mode_flags = {
        "ultra-fast": ["--n-samples", "1024", "--z-saves", "48"],
        "ci": ["--n-samples", "2048", "--z-saves", "96"],
        "full": ["--n-samples", "4096", "--z-saves", "150"],
    }
    cmd = [
        sys.executable,
        "-m",
        "cpa_sim.examples.gnlse_dispersive_wave",
        "--outdir",
        str(run_dir),
        "--raman-model",
        "blowwood",
        *mode_flags[args.mode],
    ]

    print("Running dispersive-wave command:")
    print("  " + " ".join(shlex.quote(part) for part in cmd))

    try:
        subprocess.run(cmd, check=True)
        npz_path = run_dir / "fiber_dispersive_wave_z_traces.npz"
        if not npz_path.exists():
            raise FileNotFoundError(f"Expected z-traces file was not generated: {npz_path}")
        z_m, t_fs, w_rad_per_fs, at_zt = _load_z_traces(npz_path)
        _build_svgs(z_m=z_m, t_fs=t_fs, w_rad_per_fs=w_rad_per_fs, at_zt=at_zt, outdir=outdir)
        _cleanup_run_dir(run_dir)
        _cleanup_run_dir(run_dir.parent)
        print(f"Wrote generated SVG assets to: {outdir}")
    except (subprocess.CalledProcessError, RuntimeError, FileNotFoundError) as exc:
        _cleanup_run_dir(run_dir)
        _cleanup_run_dir(run_dir.parent)
        if not args.allow_missing_gnlse:
            raise
        _save_placeholder_svgs(outdir, reason=str(exc))
        print(f"Wrote placeholder SVG assets to: {outdir}")


if __name__ == "__main__":
    main()
