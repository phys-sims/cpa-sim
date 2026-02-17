from __future__ import annotations

import argparse
from pathlib import Path

from cpa_sim.examples.wust_gnlse_fiber_example import run_example


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a small WUST gnlse fiber example and save plots."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/fiber-example"),
        help="Output directory for generated plot files.",
    )
    parser.add_argument(
        "--format",
        choices=["svg", "pdf"],
        default="svg",
        help="Vector output format. SVG is default to avoid binary artifacts.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    outputs = run_example(args.out, plot_format=args.format)
    for name, path in outputs.items():
        print(f"wrote {name}: {path}")


if __name__ == "__main__":
    main()
