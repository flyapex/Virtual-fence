"""Run a group-level power grid under stated, unmeasured model assumptions.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.power_main`, which is
also installed as the ``vf-power`` command.
"""

from vf_training.cli import power_main

if __name__ == "__main__":
    raise SystemExit(power_main())
