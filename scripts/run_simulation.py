"""Run one deterministic group simulation and print planning metrics."""

from __future__ import annotations

import argparse
from statistics import fmean

from vf_training.metrics import escape_count, group_pulse_rate, success_ratio, time_to_criterion
from vf_training.model import ARM_NAMES, SimulationParameters, SimulationResult, simulate_group
from vf_training.plots import DEFAULT_OUTPUT_DIR, FORMATS, figure_path, plot_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_NAMES, default="conventional")
    parser.add_argument("--tau", type=float, default=0.0, help="Transfer assumption, only for simulation arm.")
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--animals", type=int, default=5)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Write a day-by-day figure in addition to the text output.",
    )
    parser.add_argument(
        "--compare-arms",
        action="store_true",
        help="With --plot, overlay all three arms at the same transfer assumption.",
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


def _figure_inputs(
    args: argparse.Namespace,
    parameters: SimulationParameters,
    primary: SimulationResult,
    tau: float,
) -> tuple[list[SimulationResult], str]:
    """Return the results to draw and a deterministic file stem for them."""
    if not args.compare_arms:
        return [primary], f"days_{primary.arm}_tau{tau:.2f}_seed{args.seed}"
    # The simulation arm carries the transfer assumption; the other two arms
    # take no tau by design, matching how each arm is simulated for analysis.
    results = [
        simulate_group(
            arm,
            tau=args.tau if arm == "simulation" else 0.0,
            parameters=parameters,
            seed=args.seed,
        )
        for arm in ARM_NAMES
    ]
    return results, f"days_arms_tau{args.tau:.2f}_seed{args.seed}"


def main() -> None:
    args = parse_args()
    if args.compare_arms and not args.plot:
        raise SystemExit("--compare-arms only changes the figure; add --plot.")
    tau = args.tau if args.arm == "simulation" else 0.0
    parameters = SimulationParameters(n_animals=args.animals, days=args.days)
    result = simulate_group(args.arm, tau=tau, parameters=parameters, seed=args.seed)
    print("SIMULATED PLANNING OUTPUT - all numeric parameters are assumptions")
    print(f"arm={result.arm}; tau={result.tau:.2f}; animals={args.animals}; days={args.days}; seed={args.seed}")
    print(f"interactions={len(result.events)}")
    print(f"pulses per animal-day, first 3 days={group_pulse_rate(result, through_day=min(3, args.days)):.3f}")
    print(f"audio-only success ratio={success_ratio(result):.3f}")
    print(f"escapes={escape_count(result)}")
    print(f"time-to-criterion (80% for 2 days)={time_to_criterion(result)}")
    print(f"mean final associative strength={fmean(result.final_associative_strengths):.3f}")

    if args.plot:
        results, stem = _figure_inputs(args, parameters, result, tau)
        target = figure_path(args.outdir, stem, suffix=args.suffix)
        try:
            written = plot_simulation(results, path=target, dpi=args.dpi, show=args.show)
        except RuntimeError as error:
            raise SystemExit(str(error)) from error
        if args.show:
            print(f"figure was written to {written} before the window opened")
        else:
            print(f"figure written to {written}")


if __name__ == "__main__":
    main()
