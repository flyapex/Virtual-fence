"""Calibrate the assumed behavioural parameters against boundary records.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.calibrate_main`,
which is also installed as the ``vf-calibrate`` command.
"""

from vf_training.cli import calibrate_main

if __name__ == "__main__":
    raise SystemExit(calibrate_main())
