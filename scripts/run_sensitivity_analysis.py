"""Screen the assumed behavioural parameters with Morris elementary effects.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.sensitivity_main`,
which is also installed as the ``vf-sensitivity`` command.
"""

from vf_training.cli import sensitivity_main

if __name__ == "__main__":
    raise SystemExit(sensitivity_main())
