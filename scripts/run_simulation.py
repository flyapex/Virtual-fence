"""Run one deterministic group simulation and print planning metrics.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.simulate_main`, which
is also installed as the ``vf-simulate`` command.
"""

from vf_training.cli import simulate_main

if __name__ == "__main__":
    raise SystemExit(simulate_main())
