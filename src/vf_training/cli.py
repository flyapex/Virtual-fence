"""Command-line entry points.

Each ``*_main`` function is a console-script target declared in
``pyproject.toml``. The thin files in ``scripts/`` call the same functions, so
``vf-simulate`` and ``python scripts/run_simulation.py`` behave identically.

Every command prints simulated planning output. None of them prints a measured
result, because the project contains none.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
from math import ceil
from pathlib import Path
from statistics import fmean

from .animation import animate_simulation, animation_frames
from .data_loaders import CANDIDATE_DATASETS, inspect_dataset, read_csv_rows
from .metrics import escape_count, group_pulse_rate, success_ratio, time_to_criterion
from .model import ARM_NAMES, SimulationParameters, SimulationResult, simulate_group
from .plots import DEFAULT_OUTPUT_DIR, FORMATS, figure_path, plot_power_grid, plot_simulation
from .power import format_power_results, minimum_attainable_p, power_grid

SIMULATION_CAUTION = "SIMULATED PLANNING OUTPUT - all numeric parameters are assumptions"


def _add_figure_options(parser: argparse.ArgumentParser) -> None:
    """Add the figure flags shared by the simulation and power commands."""
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
    parser.add_argument(
        "--dpi", type=int, default=150, help="Figure resolution for raster formats."
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="With --plot, keep the figure open in a window; the command returns only when you close it.",
    )


def _require_plot(args: argparse.Namespace, flag: str) -> None:
    if getattr(args, flag) and not args.plot:
        raise SystemExit(f"--{flag.replace('_', '-')} only affects the figure; add --plot.")


def _simulation_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vf-simulate",
        description="Run one deterministic group simulation and print planning metrics.",
    )
    parser.add_argument("--arm", choices=ARM_NAMES, default="conventional")
    parser.add_argument(
        "--tau", type=float, default=0.0, help="Transfer assumption, only for simulation arm."
    )
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
    _add_figure_options(parser)
    return parser


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


def simulate_main(argv: Sequence[str] | None = None) -> int:
    """Run one group simulation, print its metrics, and optionally draw it."""
    args = _simulation_parser().parse_args(argv)
    _require_plot(args, "compare_arms")
    _require_plot(args, "show")
    tau = args.tau if args.arm == "simulation" else 0.0
    parameters = SimulationParameters(n_animals=args.animals, days=args.days)
    result = simulate_group(args.arm, tau=tau, parameters=parameters, seed=args.seed)

    print(SIMULATION_CAUTION)
    print(
        f"arm={result.arm}; tau={result.tau:.2f}; animals={args.animals}; "
        f"days={args.days}; seed={args.seed}"
    )
    print(f"interactions={len(result.events)}")
    print(
        "pulses per animal-day, first 3 days="
        f"{group_pulse_rate(result, through_day=min(3, args.days)):.3f}"
    )
    print(f"audio-only success ratio={success_ratio(result):.3f}")
    print(f"escapes={escape_count(result)}")
    print(f"time-to-criterion (first day of an 80%-for-2-days run)={time_to_criterion(result)}")
    print(f"mean final associative strength={fmean(result.final_associative_strengths):.3f}")

    if not args.plot:
        return 0

    results, stem = _figure_inputs(args, parameters, result, tau)
    target = figure_path(args.outdir, stem, suffix=args.suffix)
    if args.show:
        print(
            f"writing {target}, then opening a window "
            "- close the window to return, Ctrl+C to abort",
            flush=True,
        )
    try:
        written = plot_simulation(results, path=target, dpi=args.dpi, show=args.show)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    if not args.show:
        print(f"figure written to {written}")
    return 0


def _power_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vf-power",
        description="Run a group-level power grid under stated, unmeasured model assumptions.",
    )
    parser.add_argument("--replications", type=int, default=500)
    parser.add_argument("--animals-per-group", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument(
        "--groups-per-arm",
        type=int,
        nargs="+",
        default=[3, 4, 5, 6],
        metavar="N",
        help="Group counts per arm to grid over (default: 3 4 5 6).",
    )
    parser.add_argument(
        "--taus",
        type=float,
        nargs="+",
        default=[0.0, 0.25, 0.50, 0.75, 1.0],
        metavar="TAU",
        help="Transfer assumptions to grid over (default: 0 0.25 0.5 0.75 1).",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Write a power grid figure in addition to the text table.",
    )
    _add_figure_options(parser)
    return parser


def power_main(argv: Sequence[str] | None = None) -> int:
    """Run the planning power grid and optionally draw it."""
    args = _power_parser().parse_args(argv)
    _require_plot(args, "show")
    results = power_grid(
        groups_per_arm=args.groups_per_arm,
        taus=args.taus,
        animals_per_group=args.animals_per_group,
        replications=args.replications,
        seed=args.seed,
    )

    first = results[0].scenario
    floors = sorted({result.scenario.groups_per_arm for result in results})
    print("SIMULATED POWER ESTIMATES - CONDITIONAL ON UNMEASURED ASSUMPTIONS")
    print("Primary contrast: simulation pre-training vs conventional; group is the analysis unit.")
    print(
        f"Success requires p < {first.alpha:g} AND at least a "
        f"{first.required_relative_reduction:.0%} pulse reduction in days 1-{first.primary_days}."
    )
    print("The rejection-rate column reports the test alone, before that reduction rule.")
    floor_text = ", ".join(
        f"{count}/arm {minimum_attainable_p(replace(first, groups_per_arm=count)):.3f}"
        for count in floors
    )
    print(f"Smallest attainable two-sided p by design: {floor_text}.")
    print(
        "A row whose floor is at or above alpha cannot reject at any effect size; the note column"
    )
    print("separates that from rows where the simulated reduction is simply below target.")
    print("Mock-boundary groups share the conventional mechanism, so their reduction is a null.")
    print(format_power_results(results))

    if not args.plot:
        return 0

    stem = f"power_grid_rep{args.replications}_seed{args.seed}"
    target = figure_path(args.outdir, stem, suffix=args.suffix)
    if args.show:
        print(
            f"writing {target}, then opening a window "
            "- close the window to return, Ctrl+C to abort",
            flush=True,
        )
    try:
        written = plot_power_grid(results, path=target, dpi=args.dpi, show=args.show)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    if not args.show:
        print(f"figure written to {written}")
    return 0


def _play_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vf-play",
        description=(
            "Play one simulated group meeting a virtual boundary as an animation. "
            "The scene is schematic; the event history is the model's own."
        ),
    )
    parser.add_argument("--arm", choices=ARM_NAMES, default="simulation")
    parser.add_argument(
        "--tau", type=float, default=0.60, help="Transfer assumption, only for simulation arm."
    )
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--animals", type=int, default=5)
    parser.add_argument(
        "--days", type=int, default=3, help="Days to play (default: 3, the primary window)."
    )
    parser.add_argument(
        "--steps", type=int, default=5, help="Frames drawn per boundary interaction."
    )
    parser.add_argument("--interval", type=int, default=60, help="Milliseconds per frame.")
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Open the adjustable window: one field panel with sliders for animals, "
            "days, tau, learning rate and speed that re-simulate as you change them."
        ),
    )
    parser.add_argument(
        "--strength",
        action="store_true",
        help="With --live, start with the associative-strength bars shown.",
    )
    parser.add_argument(
        "--loop", action="store_true", help="Repeat in the window until it is closed."
    )
    parser.add_argument(
        "--gif", action="store_true", help="Write an animated GIF instead of opening a window."
    )
    parser.add_argument(
        "--still", action="store_true", help="Write one still frame instead of opening a window."
    )
    parser.add_argument(
        "--still-at", type=float, default=0.5, help="Placement of the still, 0 to 1."
    )
    parser.add_argument(
        "--max-frames", type=int, default=240, help="Cap on frames written to a GIF."
    )
    parser.add_argument(
        "--outdir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for GIF or still."
    )
    parser.add_argument("--dpi", type=int, default=110)
    return parser


def play_main(argv: Sequence[str] | None = None) -> int:
    """Animate one simulated group, in a window or as a written file."""
    args = _play_parser().parse_args(argv)
    if args.gif and args.still:
        raise SystemExit("Choose either --gif or --still, not both.")
    if args.live and (args.gif or args.still):
        raise SystemExit("--live opens a window; drop --gif and --still.")
    if args.strength and not args.live:
        raise SystemExit("--strength only affects the adjustable window; add --live.")
    tau = args.tau if args.arm == "simulation" else 0.0

    if args.live:
        from .live import LiveControls, play_live

        controls = LiveControls(
            arm=args.arm,
            tau=tau,
            animals=args.animals,
            days=args.days,
            steps=args.steps,
            interval_ms=args.interval,
            seed=args.seed,
            show_strength=args.strength,
        )
        print("ADJUSTABLE PLAYBACK - every value is an unmeasured assumption")
        print(
            f"starting from arm={controls.arm}; tau={controls.tau:.2f}; "
            f"animals={controls.animals}; days={controls.days}; seed={controls.seed}"
        )
        print("opening the window; close it to return to the prompt", flush=True)
        try:
            play_live(controls, dpi=args.dpi)
        except RuntimeError as error:
            raise SystemExit(str(error)) from error
        return 0

    parameters = SimulationParameters(n_animals=args.animals, days=args.days)
    result = simulate_group(args.arm, tau=tau, parameters=parameters, seed=args.seed)
    frames = animation_frames(result, steps_per_interaction=args.steps)

    print("SCHEMATIC PLAYBACK OF ASSUMED MODEL MECHANICS - not measured data")
    print(
        f"arm={result.arm}; tau={result.tau:.2f}; animals={args.animals}; "
        f"days={args.days}; seed={args.seed}"
    )
    print(
        f"{len(result.events)} boundary interactions -> {len(frames)} frames at {args.interval} ms"
    )

    stem = f"playback_{result.arm}_tau{tau:.2f}_seed{args.seed}"
    try:
        if args.gif:
            target = Path(args.outdir) / f"{stem}.gif"
            stride = ceil(len(frames) / max(1, args.max_frames))
            kept = len(range(0, len(frames), stride))
            print(
                f"writing {kept} of {len(frames)} frames; export redraws each frame "
                "and can take a minute or two"
            )
            animate_simulation(
                result,
                steps_per_interaction=args.steps,
                interval_ms=args.interval,
                dpi=args.dpi,
                save=target,
                max_export_frames=args.max_frames,
            )
            print(f"animation written to {target}")
        elif args.still:
            target = figure_path(args.outdir, f"{stem}_still", suffix="png")
            animate_simulation(
                result,
                steps_per_interaction=args.steps,
                interval_ms=args.interval,
                dpi=args.dpi,
                still=target,
                still_at=args.still_at,
            )
            print(f"still written to {target}")
        else:
            print("opening the playback window; close it to return to the prompt", flush=True)
            animate_simulation(
                result,
                steps_per_interaction=args.steps,
                interval_ms=args.interval,
                dpi=args.dpi,
                repeat=args.loop,
            )
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    return 0


def _inspect_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vf-inspect",
        description=(
            "List candidate calibration datasets, or inspect local files without assuming a schema."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="data/raw",
        help="File or directory to inspect (default: data/raw).",
    )
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="List the candidate dataset records and exit.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Also read this many rows from each CSV, using its own header.",
    )
    return parser


def inspect_main(argv: Sequence[str] | None = None) -> int:
    """Report what local data actually exist, and their real headers."""
    args = _inspect_parser().parse_args(argv)

    if args.candidates:
        print("CANDIDATE CALIBRATION DATASETS - metadata as published by each source")
        print("Calibration and workflow development only; never transfer evidence.")
        for spec in CANDIDATE_DATASETS:
            print(f"- {spec.key}: {spec.title}")
            print(f"    {spec.record_url}")
            print(f"    licence: {spec.licence}; published size: {spec.published_size_bytes} bytes")
        return 0

    root = Path(args.path)
    print(f"INSPECTING {root} - reported from the file itself, never from an assumed schema")
    try:
        inspections = inspect_dataset(root)
    except FileNotFoundError:
        print(f"NOT FOUND: {root}")
        return 2

    if not inspections:
        print(f"NO FILES FOUND: {root}")
        return 1

    for inspection in inspections:
        suffix = inspection.path.suffix or "file"
        print(f"FOUND {suffix}: {inspection.path} ({inspection.size_bytes} bytes)")
        print(f"    columns: {inspection.columns}")
        print(f"    note: {inspection.note}")
    if args.rows is not None:
        for inspection in inspections:
            if inspection.columns is None:
                continue
            rows = read_csv_rows(inspection.path, limit=args.rows)
            print(f"READ {len(rows)} row(s) from {inspection.path}")
            for row in rows:
                print(f"    {row}")
    return 0
