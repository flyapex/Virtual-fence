"""Run one deterministic group simulation and print planning metrics."""

from __future__ import annotations

import argparse
from statistics import fmean

from vf_training.metrics import escape_count, group_pulse_rate, success_ratio, time_to_criterion
from vf_training.model import SimulationParameters, simulate_group


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("conventional", "simulation", "mock_boundary"), default="conventional")
    parser.add_argument("--tau", type=float, default=0.0, help="Transfer assumption, only for simulation arm.")
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--animals", type=int, default=5)
    parser.add_argument("--days", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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


if __name__ == "__main__":
    main()

