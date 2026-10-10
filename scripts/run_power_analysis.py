"""Run a group-level power grid under stated, unmeasured model assumptions."""

from __future__ import annotations

import argparse

from vf_training.plots import DEFAULT_OUTPUT_DIR, FORMATS, figure_path, plot_power_grid
from vf_training.power import format_power_results, power_grid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replications", type=int, default=500)
    parser.add_argument("--animals-per-group", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Write a power grid figure in addition to the text table.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for a figure (default: results).",
    )
    parser.add_argument(
        "--format",
        dest="suffix",
        choices=FORMATS,
        default="png",
        help="Figure file format (default: png).",
    )
    parser.add_argument("--dpi", type=int, default=150, help="Figure resolution for raster formats.")
    parser.add_argument(
        "--show",
        action="store_true",
        help="With --plot, hold the figure open in a window; the command returns when you close it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = power_grid(
        animals_per_group=args.animals_per_group,
        replications=args.replications,
        seed=args.seed,
    )
    print("SIMULATED POWER ESTIMATES - CONDITIONAL ON UNMEASURED ASSUMPTIONS")
    print("Primary contrast: simulation pre-training vs conventional; group is the analysis unit.")
    print("Mock-boundary groups are simulated as the third arm and reported descriptively.")
    print("Success requires p < 0.05 and at least 30% fewer pulses in days 1-3.")
    print("With 3 groups per arm, a two-sided exact permutation test has minimum p=0.10.")
    print(format_power_results(results))

    if args.plot:
        stem = f"power_grid_rep{args.replications}_seed{args.seed}"
        target = figure_path(args.outdir, stem, suffix=args.suffix)
        try:
            written = plot_power_grid(results, path=target, dpi=args.dpi, show=args.show)
        except RuntimeError as error:
            raise SystemExit(str(error)) from error
        if args.show:
            print(f"figure was written to {written} before the window opened")
        else:
            print(f"figure written to {written}")


if __name__ == "__main__":
    main()
