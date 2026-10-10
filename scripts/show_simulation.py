"""Play one simulated group meeting a virtual boundary as an animation."""

from __future__ import annotations

import argparse
from math import ceil
from pathlib import Path

from vf_training.animation import animate_simulation, animation_frames
from vf_training.model import ARM_NAMES, SimulationParameters, simulate_group
from vf_training.plots import DEFAULT_OUTPUT_DIR, figure_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_NAMES, default="simulation")
    parser.add_argument("--tau", type=float, default=0.60, help="Transfer assumption, only for simulation arm.")
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--animals", type=int, default=5)
    parser.add_argument("--days", type=int, default=3, help="Days to play (default: 3, the primary window).")
    parser.add_argument("--steps", type=int, default=5, help="Frames drawn per boundary interaction.")
    parser.add_argument("--interval", type=int, default=60, help="Milliseconds per frame.")
    parser.add_argument("--loop", action="store_true", help="Repeat in the window until it is closed.")
    parser.add_argument("--gif", action="store_true", help="Write an animated GIF instead of opening a window.")
    parser.add_argument("--still", action="store_true", help="Write one still frame instead of opening a window.")
    parser.add_argument("--still-at", type=float, default=0.5, help="Placement of the still, 0 to 1.")
    parser.add_argument("--max-frames", type=int, default=240, help="Cap on frames written to a GIF.")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for GIF or still.")
    parser.add_argument("--dpi", type=int, default=110)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.gif and args.still:
        raise SystemExit("Choose either --gif or --still, not both.")
    tau = args.tau if args.arm == "simulation" else 0.0
    parameters = SimulationParameters(n_animals=args.animals, days=args.days)
    result = simulate_group(args.arm, tau=tau, parameters=parameters, seed=args.seed)
    frames = animation_frames(result, steps_per_interaction=args.steps)

    print("SCHEMATIC PLAYBACK OF ASSUMED MODEL MECHANICS - not measured data")
    print(f"arm={result.arm}; tau={result.tau:.2f}; animals={args.animals}; days={args.days}; seed={args.seed}")
    print(f"{len(result.events)} boundary interactions -> {len(frames)} frames at {args.interval} ms")

    stem = f"playback_{result.arm}_tau{tau:.2f}_seed{args.seed}"
    shared = {
        "steps_per_interaction": args.steps,
        "interval_ms": args.interval,
        "dpi": args.dpi,
    }
    try:
        if args.gif:
            target = Path(args.outdir) / f"{stem}.gif"
            stride = ceil(len(frames) / max(1, args.max_frames))
            kept = len(range(0, len(frames), stride))
            print(f"writing {kept} of {len(frames)} frames; export redraws each frame and can take a minute or two")
            animate_simulation(result, save=target, max_export_frames=args.max_frames, **shared)
            print(f"animation written to {target}")
        elif args.still:
            target = figure_path(args.outdir, f"{stem}_still", suffix="png")
            animate_simulation(result, still=target, still_at=args.still_at, **shared)
            print(f"still written to {target}")
        else:
            print("opening the playback window; close it to return to the prompt")
            animate_simulation(result, repeat=args.loop, **shared)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
