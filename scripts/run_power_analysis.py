"""Run a group-level power grid under stated, unmeasured model assumptions."""

from __future__ import annotations

import argparse

from vf_training.power import format_power_results, power_grid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replications", type=int, default=500)
    parser.add_argument("--animals-per-group", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261010)
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


if __name__ == "__main__":
    main()

