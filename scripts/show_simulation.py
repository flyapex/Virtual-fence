"""Play one simulated group meeting a virtual boundary as an animation.

Thin wrapper: the behaviour lives in :func:`vf_training.cli.play_main`, which is
also installed as the ``vf-play`` command.
"""

from vf_training.cli import play_main

if __name__ == "__main__":
    raise SystemExit(play_main())
