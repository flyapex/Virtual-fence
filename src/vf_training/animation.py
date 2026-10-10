"""Animated playback of one simulated group meeting a virtual boundary.

The scene is a drawing convention: the field, the fence line and the animal
positions are schematic, not a paddock layout and not animal data. What the
playback reproduces faithfully is the simulated event history - when each animal
met the boundary, whether it responded to audio alone, whether it received a
pulse, and how its assumed associative strength changed. An escape is drawn as a
single crossing, because the model does not remove escaped animals from later
interactions.

matplotlib is optional. Importing this module never needs it; only playback and
export do.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sin
from pathlib import Path

from .model import Interaction, SimulationResult
from .plots import FORMATS, _pyplot

CAUTION = (
    "SCHEMATIC PLAYBACK OF ASSUMED MODEL MECHANICS - no measured data, no real "
    "pulses, and positions are a drawing convention."
)

FIELD_WIDTH = 10.0
FIELD_HEIGHT = 6.0
FENCE_X = 8.6
APPROACH_X = 7.9
HOME_X = 2.7

ANIMAL_COLOURS: dict[str, str] = {
    "grazing": "#4d4d4d",
    "approaching": "#1f77b4",
    "audio_response": "#2ca02c",
    "pulse": "#d62728",
    "escaped": "#ff7f0e",
}

#: Reader-facing names for the drawn states, so no internal key reaches a label.
ANIMAL_LABELS: dict[str, str] = {
    "grazing": "away from fence",
    "approaching": "approaching",
    "audio_response": "audio response",
    "pulse": "pulse",
    "escaped": "crossed boundary",
}


@dataclass(frozen=True)
class AnimalPose:
    """Where one animal is drawn at one instant, and what it is doing."""

    animal_id: int
    x: float
    y: float
    state: str
    strength: float


@dataclass(frozen=True)
class AnimationFrame:
    """One drawn instant, tied to the interaction it belongs to."""

    day: int
    interaction_number: int
    phase: int
    phases: int
    event: Interaction
    animals: tuple[AnimalPose, ...]
    pulses_so_far: int
    responses_so_far: int
    escapes_so_far: int


def home_positions(n_animals: int) -> tuple[tuple[float, float], ...]:
    """Return schematic resting positions, spread down the near side of the field."""
    if n_animals < 1:
        raise ValueError("At least one animal is required.")
    spacing = FIELD_HEIGHT / (n_animals + 1)
    return tuple(
        (HOME_X + 0.35 * sin(animal_id * 1.7), spacing * (animal_id + 1))
        for animal_id in range(n_animals)
    )


def _drift(animal_id: int, frame_index: int) -> tuple[float, float]:
    """Return a smooth deterministic wobble so resting animals still read as alive."""
    return (
        0.18 * sin(0.35 * frame_index + animal_id),
        0.22 * sin(0.27 * frame_index + 1.3 * animal_id),
    )


def _actor_pose(
    event: Interaction,
    phase: int,
    phases: int,
    home: tuple[float, float],
    drift: tuple[float, float],
) -> tuple[float, float, str]:
    """Return the acting animal's position and state for one phase."""
    home_x, home_y = home
    drift_x, drift_y = drift
    decision = phases - 2
    if phase == 0:
        return home_x + drift_x, home_y + drift_y, "grazing"
    if phase < decision:
        fraction = phase / decision
        return home_x + (APPROACH_X - home_x) * fraction, home_y + drift_y, "approaching"
    if phase == decision:
        if event.audio_only_response:
            return APPROACH_X - 0.9, home_y + drift_y, "audio_response"
        return FENCE_X + 0.05, home_y + drift_y, "pulse"
    if event.escaped:
        return FENCE_X + 1.0, home_y + drift_y, "escaped"
    return home_x + drift_x, home_y + drift_y, "grazing"


def animation_frames(
    result: SimulationResult,
    *,
    steps_per_interaction: int = 5,
) -> tuple[AnimationFrame, ...]:
    """Expand a simulated group into drawable frames.

    Each boundary interaction becomes `steps_per_interaction` frames: rest,
    approach, the decision at the fence, and the outcome. This function is pure,
    so the geometry can be tested without matplotlib.
    """
    if steps_per_interaction < 3:
        raise ValueError("Use at least three steps per interaction so movement reads as motion.")
    events = result.events
    if not events:
        raise ValueError("The simulation result has no boundary interactions to animate.")

    n_animals = len(result.final_associative_strengths)
    homes = home_positions(n_animals)
    strengths = [0.0] * n_animals
    known: set[int] = set()
    pulses = responses = escapes = 0
    frames: list[AnimationFrame] = []
    frame_index = 0
    decision_phase = steps_per_interaction - 2

    for event in events:
        actor = event.animal_id
        if actor not in known:
            strengths[actor] = event.associative_strength_before
            known.add(actor)
        pulses += int(event.pulse_delivered)
        responses += int(event.audio_only_response)
        escapes += int(event.escaped)

        for phase in range(steps_per_interaction):
            if phase == decision_phase and event.pulse_delivered:
                # The pulse lands on the decision frame, so the strength bar
                # rises at the same instant the animal is drawn at the fence.
                strengths[actor] = event.associative_strength_after
            poses: list[AnimalPose] = []
            for animal_id in range(n_animals):
                home = homes[animal_id]
                drift = _drift(animal_id, frame_index)
                if animal_id == actor:
                    x, y, state = _actor_pose(event, phase, steps_per_interaction, home, drift)
                else:
                    x, y, state = home[0] + drift[0], home[1] + drift[1], "grazing"
                poses.append(
                    AnimalPose(
                        animal_id=animal_id,
                        x=x,
                        y=y,
                        state=state,
                        strength=strengths[animal_id],
                    )
                )
            frames.append(
                AnimationFrame(
                    day=event.day,
                    interaction_number=event.interaction_number,
                    phase=phase,
                    phases=steps_per_interaction,
                    event=event,
                    animals=tuple(poses),
                    pulses_so_far=pulses,
                    responses_so_far=responses,
                    escapes_so_far=escapes,
                )
            )
            frame_index += 1
    return tuple(frames)


def animate_simulation(
    result: SimulationResult,
    *,
    steps_per_interaction: int = 5,
    interval_ms: int = 60,
    repeat: bool = False,
    save: str | Path | None = None,
    still: str | Path | None = None,
    still_at: float = 0.5,
    max_export_frames: int = 400,
    dpi: int = 110,
    title: str | None = None,
) -> Path | None:
    """Play the group in a window, or write a GIF or a single still.

    With neither `save` nor `still` the playback opens a window and blocks until
    it is closed. `save` writes an animated GIF, uniformly thinning the frames
    when the run is longer than `max_export_frames`, and `still` writes one
    frame at the fraction `still_at` of the run. Returning None means a window
    was shown rather than a file written.
    """
    if save is not None and still is not None:
        raise ValueError("Pass either save or still, not both.")
    if not 0.0 <= still_at <= 1.0:
        raise ValueError("still_at must be between 0 and 1.")

    frames = animation_frames(result, steps_per_interaction=steps_per_interaction)
    save_path = Path(save) if save is not None else None
    still_path = Path(still) if still is not None else None
    if save_path is not None and save_path.suffix.lower() != ".gif":
        raise ValueError("Animation export writes .gif; use the figure scripts for png, svg or pdf.")
    if still_path is not None and still_path.suffix.lower().lstrip(".") not in FORMATS:
        raise ValueError(f"A still must end with one of {FORMATS}, got {still_path.name!r}.")

    headless = save_path is not None or still_path is not None
    plt = _pyplot(interactive=not headless)
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.lines import Line2D

    n_animals = len(result.final_associative_strengths)
    # A fixed layout, not a constrained one: constrained layout re-solves on
    # every frame, which makes export several times slower for no visible gain.
    figure, (field, bars) = plt.subplots(
        1, 2, figsize=(12.5, 6.4), gridspec_kw={"width_ratios": (3.4, 1.0)}
    )
    figure.subplots_adjust(left=0.04, right=0.98, top=0.88, bottom=0.11, wspace=0.16)

    field.set_xlim(-0.5, FIELD_WIDTH)
    field.set_ylim(0.0, FIELD_HEIGHT)
    field.axvspan(FENCE_X, FIELD_WIDTH, color="#f4d4d4", zorder=0)
    field.axvline(FENCE_X, color="#8b1a1a", linewidth=2, linestyle="--", zorder=1)
    field.axvline(APPROACH_X, color="0.55", linewidth=1, linestyle=":", zorder=1)
    field.text(APPROACH_X - 0.15, FIELD_HEIGHT - 0.2, "audio cue zone", fontsize=7, color="0.45", ha="right", va="top")
    field.text(FENCE_X + 0.15, FIELD_HEIGHT - 0.2, "beyond the boundary", fontsize=7, color="#8b1a1a", va="top")
    field.set_yticks([])
    field.set_xticks([])
    field.set_title("Schematic field: assumed animals meeting the boundary", fontsize=11)

    markers = []
    labels = []
    for animal_id in range(n_animals):
        marker, = field.plot([], [], marker="o", linestyle="none", markersize=13, color=ANIMAL_COLOURS["grazing"])
        markers.append(marker)
        labels.append(
            field.text(0.0, 0.0, str(animal_id + 1), ha="center", va="center", fontsize=7, color="white", zorder=5)
        )
    pulse_marker, = field.plot([], [], marker="X", linestyle="none", markersize=17, color="#d62728", zorder=4)
    response_ring, = field.plot(
        [], [], marker="o", linestyle="none", markerfacecolor="none",
        markeredgecolor="#2ca02c", markeredgewidth=2, markersize=24, zorder=3,
    )
    status = field.text(0.05, FIELD_HEIGHT - 0.2, "", fontsize=9, va="top", family="monospace")
    field.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="none", color=colour, label=ANIMAL_LABELS[state])
            for state, colour in ANIMAL_COLOURS.items()
        ],
        loc="lower left",
        fontsize=7,
        frameon=False,
        ncol=2,
    )

    bars.set_xlim(0.0, 1.0)
    bars.set_ylim(-0.6, n_animals - 0.4)
    bars.set_yticks(range(n_animals))
    bars.set_yticklabels([f"animal {animal_id + 1}" for animal_id in range(n_animals)], fontsize=8)
    bars.set_title("assumed associative strength", fontsize=10)
    bars.set_xlabel("strength (0-1)")
    rectangles = list(bars.barh(range(n_animals), [0.0] * n_animals, height=0.6, color="#1f77b4"))

    def update(index: int) -> tuple:
        frame = frames[index]
        for pose in frame.animals:
            marker = markers[pose.animal_id]
            marker.set_data([pose.x], [pose.y])
            marker.set_color(ANIMAL_COLOURS.get(pose.state, ANIMAL_COLOURS["grazing"]))
            labels[pose.animal_id].set_position((pose.x, pose.y))
            rectangles[pose.animal_id].set_width(max(0.0, min(1.0, pose.strength)))
        actor = frame.event.animal_id
        actor_pose = frame.animals[actor]
        if actor_pose.state == "pulse":
            pulse_marker.set_data([actor_pose.x], [actor_pose.y])
            outcome = "PULSE"
        else:
            pulse_marker.set_data([], [])
            outcome = ANIMAL_LABELS.get(actor_pose.state, actor_pose.state)
        ring = (actor_pose.x, actor_pose.y) if actor_pose.state == "audio_response" else None
        response_ring.set_data([ring[0]] if ring else [], [ring[1]] if ring else [])
        status.set_text(
            f"day {frame.day}   interaction {frame.interaction_number}\n"
            f"pulses {frame.pulses_so_far}   audio-only {frame.responses_so_far}   escapes {frame.escapes_so_far}\n"
            f"animal {actor + 1}: {outcome}"
        )
        # Returned so an interactive window can redraw only what changed; this
        # is what keeps playback smooth instead of re-drawing every artist.
        return (*markers, *labels, *rectangles, pulse_marker, response_ring, status)

    figure.suptitle(
        title
        or f"Simulated group playback: {result.arm} arm, tau={result.tau:.2f}, {len(result.events)} interactions",
        y=0.97,
    )
    figure.text(0.5, 0.025, CAUTION, ha="center", fontsize=8, color="0.35")

    if still_path is not None:
        still_path.parent.mkdir(parents=True, exist_ok=True)
        update(int(round(still_at * (len(frames) - 1))))
        figure.savefig(still_path, dpi=dpi)
        figure.clear()
        plt.close(figure)
        return still_path

    indices = list(range(len(frames)))
    if save_path is not None and len(indices) > max_export_frames:
        stride = ceil(len(indices) / max_export_frames)
        indices = indices[::stride]
    animation = FuncAnimation(
        figure, update, frames=indices, interval=interval_ms, repeat=repeat, blit=True
    )

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        animation.save(save_path, writer=PillowWriter(fps=max(1, round(1000.0 / interval_ms))), dpi=dpi)
        figure.clear()
        plt.close(figure)
        return save_path

    plt.show()  # blocks until the window is closed
    figure.clear()
    plt.close(figure)
    return None
