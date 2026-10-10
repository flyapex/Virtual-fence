"""Report candidate calibration datasets and inspect local files.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.inspect_main`, which
is also installed as the ``vf-inspect`` command.
"""

from vf_training.cli import inspect_main

if __name__ == "__main__":
    raise SystemExit(inspect_main())
