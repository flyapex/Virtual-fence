"""Live, adjustable playback: one field panel with controls that re-simulate.

Changing a control re-runs the simulation immediately and restarts the playback,
so the effect of an assumption is visible rather than described. The window shows
one panel of assumed animals meeting the boundary, plus the controls themselves.

The scene is a drawing convention, not a paddock and not measured data. Every
value a control offers is an unmeasured assumption, and the strength bars show
the model's own internal state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .animation import (
    ANIMAL_COLOURS,
    ANIMAL_LABELS,
    APPROACH_X,
    CAUTION,
    FENCE_X,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    AnimationFrame,
    animation_frames,
)
from .model import ARM_NAMES, Arm, SimulationParameters, SimulationResult, simulate_group
from .plots import FORMATS, _pyplot, set_window_title

if TYPE_CHECKING:  # pragma: no cover - imported for annotations only
    from matplotlib.animation import FuncAnimation

#: Control ranges. Each bound is a viewing convenience, not a model claim.
ANIMAL_RANGE = (1, 12)
DAY_RANGE = (1, 7)
STEP_RANGE = (3, 10)
INTERVAL_RANGE = (20, 300)
LEARNING_RATE_RANGE = (0.05, 0.50)


def display_available() -> bool:
    """Return True when an interactive window can actually be opened here.

    Used so a headless machine gets a clear message instead of a silent no-op
    from a non-interactive backend.
    """
    try:
        import tkinter
    except ImportError:
        return False
    try:
        root = tkinter.Tk()
    except Exception:
        # Any Tk failure (no display, no window station) means no usable window.
        return False
    root.destroy()
    return True


@dataclass(frozen=True)
class LiveControls:
    """The settings a viewer can change while the playback runs."""

    arm: Arm = "simulation"
    tau: float = 0.60
    animals: int = 5
    days: int = 3
    steps: int = 5
    interval_ms: int = 60
    learning_rate: float = 0.25
    seed: int = 20261010
    show_strength: bool = False

    def validate(self) -> None:
        """Raise a clear error for a setting outside the control ranges."""
        if self.arm not in ARM_NAMES:
            raise ValueError(f"arm must be one of {ARM_NAMES}, got {self.arm!r}")
        if not ANIMAL_RANGE[0] <= self.animals <= ANIMAL_RANGE[1]:
            raise ValueError(f"animals must be within {ANIMAL_RANGE}, got {self.animals}")
        if not DAY_RANGE[0] <= self.days <= DAY_RANGE[1]:
            raise ValueError(f"days must be within {DAY_RANGE}, got {self.days}")
        if not STEP_RANGE[0] <= self.steps <= STEP_RANGE[1]:
            raise ValueError(f"steps must be within {STEP_RANGE}, got {self.steps}")
        if not INTERVAL_RANGE[0] <= self.interval_ms <= INTERVAL_RANGE[1]:
            raise ValueError(f"interval_ms must be within {INTERVAL_RANGE}, got {self.interval_ms}")
        if not LEARNING_RATE_RANGE[0] <= self.learning_rate <= LEARNING_RATE_RANGE[1]:
            raise ValueError(
                f"learning_rate must be within {LEARNING_RATE_RANGE}, got {self.learning_rate}"
            )
        if not 0.0 <= self.tau <= 1.0:
            raise ValueError(f"tau must be between 0 and 1, got {self.tau}")

    def parameters(self) -> SimulationParameters:
        """Return the model parameters these controls describe."""
        return SimulationParameters(
            n_animals=self.animals,
            days=self.days,
            learning_rate=self.learning_rate,
        )

    def simulate(self) -> SimulationResult:
        """Run one group under these controls. Deterministic for a fixed seed."""
        self.validate()
        tau = self.tau if self.arm == "simulation" else 0.0
        return simulate_group(self.arm, tau=tau, parameters=self.parameters(), seed=self.seed)


class LivePlayback:
    """A single field panel, its controls, and the animation that drives them."""

    def __init__(self, controls: LiveControls | None = None, *, dpi: int = 100) -> None:
        controls = controls or LiveControls()
        controls.validate()
        self.controls = controls
        self.dpi = dpi
        self.frames: tuple[AnimationFrame, ...] = ()
        self.index = -1
        self._build()

    # -- construction -----------------------------------------------------
    def _build(self) -> None:
        plt = _pyplot(interactive=True)
        from matplotlib.widgets import Button, CheckButtons, RadioButtons

        self.plt = plt
        self.figure = plt.figure(figsize=(13.0, 7.5), dpi=self.dpi)
        self.figure.subplots_adjust(left=0.03, right=0.99, top=0.94, bottom=0.06)
        self.field = self.figure.add_axes((0.03, 0.05, 0.60, 0.86))
        self.field.set_xlim(-0.5, FIELD_WIDTH)
        self.field.set_ylim(0.0, FIELD_HEIGHT)
        self.field.axvspan(FENCE_X, FIELD_WIDTH, color="#f4d4d4", zorder=0)
        self.field.axvline(FENCE_X, color="#8b1a1a", linewidth=2, linestyle="--", zorder=1)
        self.field.axvline(APPROACH_X, color="0.55", linewidth=1, linestyle=":", zorder=1)
        self.field.text(
            APPROACH_X - 0.15,
            FIELD_HEIGHT - 0.2,
            "audio cue zone",
            fontsize=7,
            color="0.45",
            ha="right",
            va="top",
        )
        self.field.text(
            FENCE_X + 0.15,
            FIELD_HEIGHT - 0.2,
            "beyond the boundary",
            fontsize=7,
            color="#8b1a1a",
            va="top",
        )
        self.field.set_yticks([])
        self.field.set_xticks([])
        self.field.set_title("Schematic field: assumed animals meeting the boundary", fontsize=11)

        self.bars = self.figure.add_axes((0.655, 0.130, 0.325, 0.150))
        self.bars.set_title("assumed associative strength", fontsize=9)
        self.bars.set_xlim(0.0, 1.0)
        self.bars.tick_params(labelsize=7)
        self.bars.set_visible(self.controls.show_strength)

        self.markers: list[Any] = []
        self.labels: list[Any] = []
        self.rectangles: list[Any] = []
        self.bar_labels: list[Any] = []
        (self.pulse_marker,) = self.field.plot(
            [], [], marker="X", linestyle="none", markersize=17, color="#d62728", zorder=4
        )
        (self.response_ring,) = self.field.plot(
            [],
            [],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor="#2ca02c",
            markeredgewidth=2,
            markersize=24,
            zorder=3,
        )
        self.status = self.field.text(
            0.05, FIELD_HEIGHT - 0.2, "", fontsize=9, va="top", family="monospace"
        )
        self._build_animal_artists()

        left = 0.655
        width = 0.325
        self.figure.text(left, 0.972, "arm", fontsize=8, color="0.35")
        self.arm_radio = RadioButtons(
            self.figure.add_axes((left, 0.850, width, 0.110)),
            list(ARM_NAMES),
            active=list(ARM_NAMES).index(self.controls.arm),
        )
        self.animal_slider = self._slider(
            left, 0.795, width, "animals", ANIMAL_RANGE, self.controls.animals
        )
        self.day_slider = self._slider(left, 0.740, width, "days", DAY_RANGE, self.controls.days)
        self.tau_slider = self._slider(
            left, 0.685, width, "tau (transfer)", (0.0, 1.0), self.controls.tau, step=0.05
        )
        self.rate_slider = self._slider(
            left,
            0.630,
            width,
            "learning rate",
            LEARNING_RATE_RANGE,
            self.controls.learning_rate,
            step=0.05,
        )
        self.speed_slider = self._slider(
            left, 0.575, width, "ms per frame", INTERVAL_RANGE, self.controls.interval_ms, step=10
        )
        self.strength_toggle = CheckButtons(
            self.figure.add_axes((left, 0.505, width, 0.05)),
            ["show strength"],
            [self.controls.show_strength],
        )
        self.replay_button = Button(self.figure.add_axes((left, 0.415, 0.155, 0.055)), "Replay")
        self.pause_button = Button(
            self.figure.add_axes((left + 0.17, 0.415, 0.155, 0.055)), "Pause"
        )
        self.reseed_button = Button(self.figure.add_axes((left, 0.335, 0.155, 0.055)), "New seed")
        self.preset_button = Button(
            self.figure.add_axes((left + 0.17, 0.335, 0.155, 0.055)), "Reset"
        )
        self.figure.text(
            left,
            0.030,
            "Every value here is an unmeasured assumption.\n"
            "Changing one re-runs the group immediately.",
            fontsize=8,
            color="0.35",
            va="bottom",
        )

        self.arm_radio.on_clicked(self._on_control)
        self.strength_toggle.on_clicked(self._on_strength)
        self.replay_button.on_clicked(self._replay)
        self.pause_button.on_clicked(self._toggle_pause)
        self.reseed_button.on_clicked(self._reseed)
        self.preset_button.on_clicked(self._reset)
        self.figure.text(0.5, 0.005, CAUTION, ha="center", fontsize=8, color="0.35")
        set_window_title(self.figure, default="vf-sim-training live playback")
        self.animation: FuncAnimation | None = None
        # The animation timer. Held as Any because the event-source protocol that
        # FuncAnimation advertises does not declare start/stop/interval.
        self.timer: Any = None
        self._rebuild()

    def _slider(
        self,
        left: float,
        bottom: float,
        width: float,
        label: str,
        limits: tuple[float, float],
        value: float,
        *,
        step: float | None = None,
    ) -> Any:
        from matplotlib.widgets import Slider

        slider = Slider(
            self.figure.add_axes((left, bottom, width, 0.03)),
            label,
            limits[0],
            limits[1],
            valinit=value,
            valstep=step,
            valfmt="%g",
        )
        slider.label.set_fontsize(8)
        slider.valtext.set_fontsize(8)
        slider.on_changed(lambda _value: self._on_control(None))
        return slider

    def _build_animal_artists(self) -> None:
        for artist in (*self.markers, *self.labels, *self.rectangles, *self.bar_labels):
            artist.remove()
        self.markers = []
        self.labels = []
        self.rectangles = []
        self.bar_labels = []
        n_animals = self.controls.animals
        for animal_id in range(n_animals):
            (marker,) = self.field.plot(
                [],
                [],
                marker="o",
                linestyle="none",
                markersize=13,
                color=ANIMAL_COLOURS["grazing"],
            )
            self.markers.append(marker)
            self.labels.append(
                self.field.text(
                    0.0,
                    0.0,
                    str(animal_id + 1),
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    zorder=5,
                )
            )
        self.rectangles = list(
            self.bars.barh(range(n_animals), [0.0] * n_animals, height=0.6, color="#1f77b4")
        )
        self.bar_labels = []
        self.bars.set_ylim(-0.6, n_animals - 0.4)
        # Numbers, matching the labels drawn on the animals in the field.
        self.bars.set_yticks(range(n_animals))
        self.bars.set_yticklabels([str(index + 1) for index in range(n_animals)])

    # -- state ------------------------------------------------------------
    def _read_widgets(self) -> LiveControls:
        return replace(
            self.controls,
            arm=cast("Arm", self.arm_radio.value_selected),
            animals=int(self.animal_slider.val),
            days=int(self.day_slider.val),
            tau=float(self.tau_slider.val),
            learning_rate=float(self.rate_slider.val),
            interval_ms=int(self.speed_slider.val),
            show_strength=bool(self.strength_toggle.get_status()[0]),
        )

    def _rebuild(self) -> None:
        self.controls.validate()
        result = self.controls.simulate()
        self.frames = animation_frames(result, steps_per_interaction=self.controls.steps)
        self.index = -1
        self.result = result
        if len(self.markers) != self.controls.animals:
            self._build_animal_artists()

    def _on_control(self, _value: object) -> None:
        """Re-simulate and restart from the first frame after any change."""
        new_controls = self._read_widgets()
        if new_controls == self.controls:
            return
        self.controls = new_controls
        self._rebuild()
        if self.timer is not None:
            self.timer.interval = self.controls.interval_ms
        self._draw(self.frames[0] if self.frames else None)

    def _on_strength(self, _label: str | None) -> None:
        self.controls = self._read_widgets()
        self.bars.set_visible(self.controls.show_strength)
        self.figure.canvas.draw_idle()

    def _replay(self, _event: object) -> None:
        self.index = -1

    def _toggle_pause(self, _event: object) -> None:
        if self.timer is None:
            return
        if self.pause_button.label.get_text() == "Pause":
            self.timer.stop()
            self.pause_button.label.set_text("Resume")
        else:
            self.timer.start()
            self.pause_button.label.set_text("Pause")
        self.figure.canvas.draw_idle()

    def _reseed(self, _event: object) -> None:
        self.controls = replace(self.controls, seed=self.controls.seed + 1)
        self._rebuild()

    def _reset(self, _event: object) -> None:
        defaults = LiveControls()
        self.controls = replace(defaults, show_strength=self.controls.show_strength)
        for slider, value in (
            (self.animal_slider, self.controls.animals),
            (self.day_slider, self.controls.days),
            (self.tau_slider, self.controls.tau),
            (self.rate_slider, self.controls.learning_rate),
            (self.speed_slider, self.controls.interval_ms),
        ):
            slider.set_val(value)
        self.arm_radio.set_active(ARM_NAMES.index(self.controls.arm))
        self._rebuild()

    # -- drawing ----------------------------------------------------------
    def _draw(self, frame: AnimationFrame | None) -> tuple[Any, ...]:
        if frame is None:
            return ()
        for pose in frame.animals:
            marker = self.markers[pose.animal_id]
            marker.set_data([pose.x], [pose.y])
            marker.set_color(ANIMAL_COLOURS.get(pose.state, ANIMAL_COLOURS["grazing"]))
            self.labels[pose.animal_id].set_position((pose.x, pose.y))
            self.rectangles[pose.animal_id].set_width(max(0.0, min(1.0, pose.strength)))
        actor = frame.event.animal_id
        pose = frame.animals[actor]
        if pose.state == "pulse":
            self.pulse_marker.set_data([pose.x], [pose.y])
            outcome = "PULSE"
        else:
            self.pulse_marker.set_data([], [])
            outcome = ANIMAL_LABELS.get(pose.state, pose.state)
        ring = (pose.x, pose.y) if pose.state == "audio_response" else None
        self.response_ring.set_data([ring[0]] if ring else [], [ring[1]] if ring else [])
        self.status.set_text(
            f"day {frame.day}   interaction {frame.interaction_number} / {len(self.result.events)}\n"
            f"pulses {frame.pulses_so_far}   audio-only {frame.responses_so_far}   "
            f"escapes {frame.escapes_so_far}\n"
            f"animal {actor + 1}: {outcome}\n"
            f"arm {self.controls.arm}   tau {self.controls.tau:.2f}   "
            f"learning rate {self.controls.learning_rate:.2f}   seed {self.controls.seed}"
        )
        return (
            *self.markers,
            *self.labels,
            *self.rectangles,
            self.pulse_marker,
            self.response_ring,
            self.status,
        )

    def _tick(self, _ignored: int) -> tuple[Any, ...]:
        if not self.frames:
            return ()
        self.index = (self.index + 1) % len(self.frames)
        return self._draw(self.frames[self.index])

    # -- running ----------------------------------------------------------
    def start(self, *, start_paused: bool = False, show: bool = True) -> None:
        """Start the animation and, unless `show` is False, open the window."""
        from matplotlib.animation import FuncAnimation

        if show and not display_available():
            raise RuntimeError(
                "No interactive display is available here, so the adjustable window "
                "cannot open. Use --gif or --still to write a file instead."
            )
        animation = FuncAnimation(
            self.figure,
            self._tick,
            frames=count(),
            interval=self.controls.interval_ms,
            cache_frame_data=False,
        )
        self.animation = animation
        self.timer = animation.event_source
        if start_paused and self.timer is not None:
            self.timer.stop()
            self.pause_button.label.set_text("Resume")
        if show:
            self.plt.show()  # blocks until the window is closed

    def save_preview(self, path: str | Path, *, frame_index: int = 0) -> Path:
        """Write the current view to a file, controls and all."""
        target = Path(path)
        if target.suffix.lower().lstrip(".") not in FORMATS:
            raise ValueError(f"A preview must end with one of {FORMATS}, got {target.name!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        frames = self.frames or animation_frames(
            self.controls.simulate(), steps_per_interaction=self.controls.steps
        )
        self._draw(frames[min(frame_index, len(frames) - 1)])
        self.figure.savefig(target, dpi=self.dpi)
        return target


def play_live(
    controls: LiveControls | None = None,
    *,
    dpi: int = 100,
    start_paused: bool = False,
) -> LivePlayback:
    """Open the adjustable playback window and block until it is closed."""
    view = LivePlayback(controls, dpi=dpi)
    view.start(start_paused=start_paused)
    return view
