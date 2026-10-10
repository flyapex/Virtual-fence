"""Optional figure output for simulated planning runs.

Every figure this module writes is a picture of assumed parameters, not a
research result, so each one carries the caution note on its own canvas.

matplotlib is an optional dependency. Importing this module never needs it;
only the plotting functions do, and they fail with an install hint when it is
missing. Install it with ``python -m pip install -e ".[plots]"``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .metrics import daily_summary
from .model import Arm, SimulationResult
from .power import PowerResult

CAUTION = (
    "SIMULATED PLANNING OUTPUT - every numeric parameter is an unmeasured "
    "assumption, not a measurement."
)

#: Days covered by the preregistered primary outcome, shaded on day figures.
PRIMARY_WINDOW_DAYS = 3

#: Planning reference line for a power figure. It is a convention, not a target.
POWER_REFERENCE = 0.80

FORMATS = ("png", "svg", "pdf")
DEFAULT_OUTPUT_DIR = Path("results")

_ARM_COLORS: dict[Arm, str] = {
    "conventional": "#1f77b4",
    "simulation": "#d62728",
    "mock_boundary": "#6f6f6f",
}
_TAU_STYLES = ("-", "--", ":", "-.")
_MARKERS = ("o", "s", "^", "D")


def _pyplot(*, interactive: bool = False):
    """Return pyplot, or explain how to install matplotlib.

    Files are drawn on the Agg canvas so they work without a display. An
    interactive request keeps the default backend, which is what can open a
    window.
    """
    try:
        import matplotlib

        if not interactive:
            matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as error:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Figure output requires matplotlib, which is an optional dependency. "
            'Install it with: python -m pip install -e ".[plots]"'
        ) from error
    return plt


def figure_path(directory: str | Path, stem: str, *, suffix: str = "png") -> Path:
    """Return a figure path in `directory`, rejecting unsupported formats."""
    extension = suffix.lower().lstrip(".")
    if extension not in FORMATS:
        raise ValueError(f"Figure format must be one of {FORMATS}, got {suffix!r}.")
    return Path(directory) / f"{stem}.{extension}"


def _resolved(path: str | Path) -> Path:
    """Validate a figure path and create its parent directory."""
    target = Path(path)
    if target.suffix.lower().lstrip(".") not in FORMATS:
        raise ValueError(f"Figure path must end with one of {FORMATS}, got {target.name!r}.")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _finish(plt, figure, target: Path, dpi: int, *, show: bool) -> Path:
    """Write the figure, optionally hold it open in a window, then release it."""
    figure.savefig(target, dpi=dpi)
    if show:
        plt.show()  # blocks until every window is closed
    figure.clear()
    plt.close(figure)
    return target


def _label(result: SimulationResult) -> str:
    return f"{result.arm} (tau={result.tau:.2f})"


def _style(index: int) -> dict[str, object]:
    """Vary the line style and marker per series so overlaid arms stay readable."""
    return {
        "linestyle": _TAU_STYLES[index % len(_TAU_STYLES)],
        "marker": _MARKERS[index % len(_MARKERS)],
        "markersize": 4,
    }


def _coincident_labels(results: Sequence[SimulationResult]) -> tuple[str, ...]:
    """Return arm labels whose day-by-day summaries are numerically identical.

    Two arms with no transferred association and the same seed produce the same
    history, so one line hides the other. Naming them keeps a figure honest
    about what it does and does not show.
    """
    by_history: dict[tuple[object, ...], list[str]] = {}
    for result in results:
        by_history.setdefault(daily_summary(result), []).append(result.arm)
    labels: list[str] = []
    for arms in by_history.values():
        if len(arms) > 1:
            labels.append(" and ".join(sorted(arms)))
    return tuple(sorted(labels))


def plot_simulation(
    results: Sequence[SimulationResult],
    *,
    path: str | Path,
    dpi: int = 150,
    show: bool = False,
    title: str | None = None,
) -> Path:
    """Write a four-panel day-by-day figure for one or more simulated groups.

    Panels show the group pulse rate that the power module analyses, its
    cumulative total, the mean associative strength at each boundary
    interaction, and the resulting mean audio-response probability. Passing
    several results overlays them, which is how the three arms are compared.
    With `show`, the figure is written and then held open in a window.
    """
    if not results:
        raise ValueError("At least one simulation result is required.")

    plt = _pyplot(interactive=show)
    target = _resolved(path)
    summaries = [(result, daily_summary(result)) for result in results]
    last_day = max(day.day for _, days in summaries for day in days)

    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.0), layout="constrained")
    panels: tuple[tuple[str | None, str, str, tuple[float, float] | None], ...] = (
        ("pulses_per_animal_day", "Pulses per animal-day", "pulses / animal-day", None),
        (None, "Cumulative pulses", "pulses", None),
        ("mean_associative_strength_before", "Mean associative strength", "strength", (0.0, 1.05)),
        ("mean_response_probability", "Mean audio-response probability", "probability", (0.0, 1.05)),
    )

    for panel_index, (axis, (field, panel_title, ylabel, limits)) in enumerate(
        zip(axes.ravel(), panels, strict=True)
    ):
        for series_index, (result, days) in enumerate(summaries):
            x_values = [day.day for day in days]
            if field is None:
                total = 0
                y_values = []
                for day in days:
                    total += day.pulses
                    y_values.append(float(total))
            else:
                y_values = [float(getattr(day, field)) for day in days]
            axis.plot(
                x_values,
                y_values,
                label=_label(result),
                color=_ARM_COLORS.get(result.arm, f"C{series_index}"),
                **_style(series_index),
            )
        axis.axvspan(
            0.5,
            min(PRIMARY_WINDOW_DAYS, last_day) + 0.5,
            color="0.88",
            zorder=0,
            label="primary window (days 1-3)" if panel_index == 0 else None,
        )
        axis.set_title(panel_title)
        axis.set_xlabel("training day")
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(1, last_day + 1))
        if limits is not None:
            axis.set_ylim(*limits)
        else:
            axis.set_ylim(bottom=0.0)

    axes[0][0].legend(frameon=False, fontsize=8)
    figure.suptitle(title or "Simulated boundary interactions by arm")
    coincidence = _coincident_labels(results)
    note = [CAUTION]
    if coincidence:
        note.append(
            "Coincident series: "
            + "; ".join(coincidence)
            + " - no audio-to-pulse association is transferred in these arms, so their lines overlap."
        )
    figure.supxlabel("\n".join(note), fontsize=8, color="0.35")
    return _finish(plt, figure, target, dpi, show=show)


def plot_power_grid(
    results: Sequence[PowerResult],
    *,
    path: str | Path,
    dpi: int = 150,
    show: bool = False,
    title: str | None = None,
) -> Path:
    """Write a grid figure of estimated power and mean pulse reductions.

    One line per transfer assumption (`tau`) against groups per arm. The second
    panel shows the primary contrast, and the third repeats the descriptive
    mock-boundary arm that is never part of the primary comparison.
    With `show`, the figure is written and then held open in a window.
    """
    if not results:
        raise ValueError("At least one power result is required.")

    plt = _pyplot(interactive=show)
    target = _resolved(path)
    taus = sorted({result.scenario.tau for result in results})
    group_counts = sorted({result.scenario.groups_per_arm for result in results})
    first = results[0].scenario

    figure, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), layout="constrained")
    required_label = f"primary requirement ({first.required_relative_reduction:.0%})"
    panels = (
        ("estimated_power", "Estimated power", "rejection probability", POWER_REFERENCE, "80% planning reference"),
        ("mean_relative_reduction", "Mean simulation reduction", "relative reduction", first.required_relative_reduction, required_label),
        ("mean_mock_relative_reduction", "Mean mock reduction (descriptive)", "relative reduction", first.required_relative_reduction, f"{required_label}, for scale only"),
    )

    for axis, (field, panel_title, ylabel, reference, reference_label) in zip(
        axes, panels, strict=True
    ):
        for tau in taus:
            points = sorted(
                (result for result in results if result.scenario.tau == tau),
                key=lambda result: result.scenario.groups_per_arm,
            )
            axis.plot(
                [result.scenario.groups_per_arm for result in points],
                [float(getattr(result, field)) for result in points],
                marker="o",
                markersize=4,
                label=f"tau={tau:.2f}",
            )
        axis.axhline(reference, color="0.45", linestyle="--", linewidth=1, zorder=0)
        axis.annotate(
            reference_label,
            xy=(group_counts[-1], reference),
            xytext=(-3, 4),
            textcoords="offset points",
            ha="right",
            fontsize=7,
            color="0.35",
        )
        axis.set_title(panel_title)
        axis.set_xlabel("groups per arm")
        axis.set_ylabel(ylabel)
        axis.set_xticks(group_counts)

    axes[0].set_ylim(-0.03, 1.05)
    axes[0].legend(frameon=False, fontsize=8, title="transfer assumption")
    note = (
        f"Success needs p < {first.alpha:g} and at least a "
        f"{first.required_relative_reduction:.0%} pulse reduction in days 1-{first.primary_days}. "
        f"With 3 groups per arm, a two-sided exact permutation test has minimum p=0.10."
    )
    figure.suptitle(title or "Simulated power grid, group-level primary contrast")
    figure.supxlabel(f"{CAUTION}\n{note}", fontsize=8, color="0.35")
    return _finish(plt, figure, target, dpi, show=show)
