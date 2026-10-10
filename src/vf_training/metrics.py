"""Outcome definitions calculated from simulated boundary interactions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import nan
from statistics import fmean
from typing import Iterable

from .model import Interaction, SimulationResult


@dataclass(frozen=True)
class AnimalDayMetric:
    """Counts and response rate for one animal on one training day."""

    group_id: str
    animal_id: int
    day: int
    interactions: int
    pulses: int
    audio_only_responses: int
    escapes: int
    success_ratio: float


@dataclass(frozen=True)
class DaySummary:
    """Group-level aggregate for one training day, used by reports and figures.

    Every field is a summary of simulated events, not an observation. The two
    `mean_` fields average over that day's interactions, so they describe the
    state at the moment each animal met the boundary, not a day-end state.
    """

    day: int
    interactions: int
    animal_days: int
    pulses: int
    audio_only_responses: int
    escapes: int
    pulses_per_animal_day: float
    audio_only_response_ratio: float
    mean_associative_strength_before: float
    mean_response_probability: float


def _events(source: SimulationResult | Iterable[Interaction]) -> tuple[Interaction, ...]:
    return source.events if isinstance(source, SimulationResult) else tuple(source)


def pulses_per_animal_per_day(
    source: SimulationResult | Iterable[Interaction],
) -> tuple[AnimalDayMetric, ...]:
    """Calculate pulse count and audio-only response rate by animal-day."""
    grouped: dict[tuple[str, int, int], list[Interaction]] = defaultdict(list)
    for event in _events(source):
        grouped[(event.group_id, event.animal_id, event.day)].append(event)

    metrics: list[AnimalDayMetric] = []
    for (group_id, animal_id, day), events in sorted(grouped.items()):
        interactions = len(events)
        audio_only = sum(event.audio_only_response for event in events)
        metrics.append(
            AnimalDayMetric(
                group_id=group_id,
                animal_id=animal_id,
                day=day,
                interactions=interactions,
                pulses=sum(event.pulse_delivered for event in events),
                audio_only_responses=audio_only,
                escapes=sum(event.escaped for event in events),
                success_ratio=audio_only / interactions if interactions else nan,
            )
        )
    return tuple(metrics)


def daily_summary(
    source: SimulationResult | Iterable[Interaction],
) -> tuple[DaySummary, ...]:
    """Aggregate a group's events by training day, ordered by day.

    `pulses_per_animal_day` matches the group-level analysis unit used by the
    power module, so a figure drawn from this summary and the printed pulse rate
    describe the same quantity. Days without events are absent rather than zero.
    """
    daily: dict[int, list[Interaction]] = defaultdict(list)
    for event in _events(source):
        daily[event.day].append(event)

    summaries: list[DaySummary] = []
    for day in sorted(daily):
        events = daily[day]
        interactions = len(events)
        animal_days = len({event.animal_id for event in events})
        pulses = sum(event.pulse_delivered for event in events)
        audio_only = sum(event.audio_only_response for event in events)
        summaries.append(
            DaySummary(
                day=day,
                interactions=interactions,
                animal_days=animal_days,
                pulses=pulses,
                audio_only_responses=audio_only,
                escapes=sum(event.escaped for event in events),
                pulses_per_animal_day=pulses / animal_days if animal_days else nan,
                audio_only_response_ratio=audio_only / interactions if interactions else nan,
                mean_associative_strength_before=fmean(
                    event.associative_strength_before for event in events
                ),
                mean_response_probability=fmean(
                    event.response_probability for event in events
                ),
            )
        )
    return tuple(summaries)


def success_ratio(source: SimulationResult | Iterable[Interaction]) -> float:
    """Return audio-only responses divided by all boundary interactions."""
    events = _events(source)
    if not events:
        return nan
    return sum(event.audio_only_response for event in events) / len(events)


def escape_count(source: SimulationResult | Iterable[Interaction]) -> int:
    """Return the number of simulated non-containment events."""
    return sum(event.escaped for event in _events(source))


def time_to_criterion(
    source: SimulationResult | Iterable[Interaction],
    *,
    criterion: float = 0.80,
    consecutive_days: int = 2,
) -> int | None:
    """Return first day meeting a daily success criterion for consecutive days.

    The definition is a planning convention. A final preregistration should set
    the criterion before experimental data are collected.
    """
    if not 0.0 <= criterion <= 1.0 or consecutive_days < 1:
        raise ValueError("criterion must be in [0, 1] and consecutive_days must be positive.")
    daily: dict[int, list[Interaction]] = defaultdict(list)
    for event in _events(source):
        daily[event.day].append(event)

    run_length = 0
    run_start: int | None = None
    for day in sorted(daily):
        day_success = sum(event.audio_only_response for event in daily[day]) / len(daily[day])
        if day_success >= criterion:
            run_length += 1
            run_start = day if run_start is None else run_start
            if run_length >= consecutive_days:
                return run_start
        else:
            run_length = 0
            run_start = None
    return None


def group_pulse_rate(
    source: SimulationResult | Iterable[Interaction], *, through_day: int = 3
) -> float:
    """Return pulses per animal per day through `through_day`.

    It is the group-level analysis unit used by the power module. A missing
    event history returns NaN rather than silently creating a zero rate.
    """
    if through_day < 1:
        raise ValueError("through_day must be at least one.")
    events = tuple(event for event in _events(source) if event.day <= through_day)
    if not events:
        return nan
    animal_days = {(event.animal_id, event.day) for event in events}
    return sum(event.pulse_delivered for event in events) / len(animal_days)

