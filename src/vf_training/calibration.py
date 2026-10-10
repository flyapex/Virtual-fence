"""Calibrate the assumed behavioural parameters against real boundary records.

This module closes the gap that keeps the planning model from being publishable:
every behavioural parameter was an assumption. Given animal-day records of audio
cues and pulses at a real virtual-fence boundary, it fits the model's parameters
to the observed pulse and audio-only profiles and reports how well they are
identified.

Two honesties are built in. Parameters the data can measure directly (encounter
rate, escape rate) are taken from the data rather than fitted. And the fit
returns a marginal profile per parameter, so a flat profile is visible as
non-identifiability instead of being hidden behind a single best value.

The loader maps a documented USDA column set onto the concepts this model needs.
It reports the columns it matched, and refuses to guess when it cannot find them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from statistics import fmean

from .data_loaders import read_csv_rows
from .metrics import daily_summary
from .model import SimulationParameters, simulate_group

#: Column names the USDA record is documented to use, checked case-insensitively.
#: See docs/datasets.md; the loader reports what it matched and never assumes.
USDA_COLUMNS: Mapping[str, tuple[str, ...]] = {
    "audio": ("No. Audios", "No. Audios ", "Audios"),
    "pulse": ("No. Pulses", "No. Pulses ", "Pulses"),
    "day": ("Day", "Date", "Time (UTC)", "Time"),
    "animal": ("Neckband ID", "Animal_ID", "Animal ID", "Neckband ID "),
    "escape": ("Escape_no", "Escapes", "Escape_Type"),
}


@dataclass(frozen=True)
class AnimalDayObservation:
    """One animal-day of real boundary records: how often it was cued and pulsed."""

    animal: str
    day: int
    audios: int
    pulses: int
    escapes: int = 0

    @property
    def interactions(self) -> int:
        return self.audios + self.pulses

    @property
    def audio_only_ratio(self) -> float:
        return self.audios / self.interactions if self.interactions else 0.0


@dataclass(frozen=True)
class ObservedProfile:
    """What the real data say, in the quantities the model produces.

    `interactions_per_animal_day` and `escape_rate` are measured directly and are
    not fitted. The two tuples are indexed from day 1.
    """

    animals: int
    days: int
    animal_days: int
    interactions_per_animal_day: float
    escape_rate: float
    pulses_per_animal_day: tuple[float, ...]
    audio_only_ratio: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.animals < 1 or self.days < 1:
            raise ValueError("A profile needs at least one animal and one day.")
        if len(self.pulses_per_animal_day) != self.days:
            raise ValueError("pulses_per_animal_day must cover every day of the profile.")
        if len(self.audio_only_ratio) != self.days:
            raise ValueError("audio_only_ratio must cover every day of the profile.")


def profile_from_observations(observations: Sequence[AnimalDayObservation]) -> ObservedProfile:
    """Aggregate animal-day records into the profile the model is fitted to."""
    if not observations:
        raise ValueError("No observations to profile.")

    animals = len({item.animal for item in observations})
    days = max(item.day for item in observations)
    by_day: dict[int, list[AnimalDayObservation]] = {}
    for item in observations:
        by_day.setdefault(item.day, []).append(item)

    pulses: list[float] = []
    ratios: list[float] = []
    for day in range(1, days + 1):
        records = by_day.get(day, [])
        pulses.append(fmean(record.pulses for record in records) if records else 0.0)
        ratios.append(fmean(record.audio_only_ratio for record in records) if records else 0.0)

    total_interactions = sum(item.interactions for item in observations)
    total_escapes = sum(item.escapes for item in observations)
    total_pulses = sum(item.pulses for item in observations)
    return ObservedProfile(
        animals=animals,
        days=days,
        animal_days=len(observations),
        interactions_per_animal_day=total_interactions / len(observations),
        escape_rate=total_escapes / total_pulses if total_pulses else 0.0,
        pulses_per_animal_day=tuple(pulses),
        audio_only_ratio=tuple(ratios),
    )


def _match_columns(header: Iterable[str], wanted: Mapping[str, str]) -> dict[str, str]:
    """Return the actual header entry for each requested concept."""
    lookup = {name.strip().lower(): name for name in header}
    matched: dict[str, str] = {}
    for concept, candidates in USDA_COLUMNS.items():
        if concept not in wanted:
            continue
        for candidate in candidates:
            if candidate.strip().lower() in lookup:
                matched[concept] = lookup[candidate.strip().lower()]
                break
    return matched


def _day_lookup(values: Iterable[str]) -> dict[str, int]:
    """Map the day field onto 1-based day numbers.

    Accepts plain numbers, and ISO dates or timestamps, which are numbered from
    the earliest date present. Anything else raises, rather than silently
    collapsing every record onto day zero.
    """
    unique = {str(value).strip() for value in values}
    try:
        return {value: int(float(value)) for value in unique}
    except ValueError:
        pass

    as_dates: dict[str, str] = {}
    for value in unique:
        text = value[:10]
        try:
            date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(
                f"Day field {value!r} is neither a number nor an ISO date. "
                "Point the loader at a file with a usable day column."
            ) from error
        as_dates[value] = text
    ordered = sorted(set(as_dates.values()))
    index = {text: position + 1 for position, text in enumerate(ordered)}
    return {value: index[text] for value, text in as_dates.items()}


def observations_from_rows(
    rows: Sequence[Mapping[str, str]],
) -> tuple[tuple[AnimalDayObservation, ...], Mapping[str, str]]:
    """Map rows with a recorded header onto animal-day observations.

    Returns the observations and the columns that were matched, so a caller can
    print exactly which fields the numbers came from. Raises `ValueError` when a
    required concept is missing rather than guessing a column.
    """
    if not rows:
        raise ValueError("No rows to read.")
    header = list(rows[0].keys())
    matched = _match_columns(header, {concept: concept for concept in USDA_COLUMNS})
    missing = [name for name in ("audio", "pulse", "day", "animal") if name not in matched]
    if missing:
        raise ValueError(
            f"Could not find columns for {missing} in {header}. "
            "Rename them or extend USDA_COLUMNS; this loader does not guess."
        )

    days = _day_lookup(row[matched["day"]] for row in rows)
    grouped: dict[tuple[str, int], list[int]] = {}
    escape_column = matched.get("escape")
    for row in rows:
        animal = str(row[matched["animal"]]).strip()
        day = days[str(row[matched["day"]]).strip()]
        audios = int(float(row[matched["audio"]] or 0))
        pulses = int(float(row[matched["pulse"]] or 0))
        escapes = int(float(row[escape_column] or 0)) if escape_column else 0
        bucket = grouped.setdefault((animal, day), [0, 0, 0])
        bucket[0] += audios
        bucket[1] += pulses
        bucket[2] += escapes

    observations = tuple(
        AnimalDayObservation(
            animal=animal, day=day, audios=values[0], pulses=values[1], escapes=values[2]
        )
        for (animal, day), values in sorted(grouped.items())
        if day >= 1
    )
    if not observations:
        raise ValueError("No usable animal-day rows were produced from the input.")
    return observations, matched


def load_observations(
    path: str | Path,
) -> tuple[tuple[AnimalDayObservation, ...], Mapping[str, str], Path]:
    """Read the first CSV under `path` that carries the columns this model needs.

    A directory is searched recursively, because a published dataset like the
    USDA record ships several CSVs and only one holds the boundary counts. Every
    rejected file is reported by name with its reason, so a schema mismatch is
    visible instead of silent.
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"No such file or directory: {root}")
    files = [root] if root.is_file() else sorted(item for item in root.rglob("*.csv"))
    if not files:
        raise ValueError(f"No CSV files found under {root}.")

    rejections: list[str] = []
    for candidate in files:
        rows = read_csv_rows(candidate)
        if not rows:
            rejections.append(f"{candidate.name}: no rows")
            continue
        try:
            observations, matched = observations_from_rows(rows)
        except ValueError as error:
            rejections.append(f"{candidate.name}: {error}")
            continue
        return observations, matched, candidate
    raise ValueError(
        "No CSV carried the required audio, pulse, day and animal columns:\n  "
        + "\n  ".join(rejections)
    )


@dataclass(frozen=True)
class CalibrationGrid:
    """The search grid, and how many seeds each grid point is averaged over."""

    learning_rate: tuple[float, ...] = (0.10, 0.20, 0.30, 0.40)
    baseline_response_probability: tuple[float, ...] = (0.00, 0.05, 0.10)
    associative_response_weight: tuple[float, ...] = (0.40, 0.55, 0.70)
    social_response_weight: tuple[float, ...] = (0.00, 0.10, 0.20)
    seeds: tuple[int, ...] = (20261010,)
    #: Weight on the audio-only ratio term, relative to the pulse-rate term.
    ratio_weight: float = 1.0

    def points(self) -> tuple[SimulationParameters, ...]:
        """Every feasible parameter set on the grid.

        Sets whose response components would sum above one are dropped: they are
        not valid probability models, so fitting them would be meaningless.
        """
        points: list[SimulationParameters] = []
        for rate in self.learning_rate:
            for baseline in self.baseline_response_probability:
                for associative in self.associative_response_weight:
                    for social in self.social_response_weight:
                        candidate = SimulationParameters(
                            learning_rate=rate,
                            baseline_response_probability=baseline,
                            associative_response_weight=associative,
                            social_response_weight=social,
                        )
                        if baseline + associative + social > 1.0:
                            continue
                        points.append(candidate)
        if not points:
            raise ValueError("The calibration grid contains no feasible parameter set.")
        return tuple(points)


@dataclass(frozen=True)
class ParameterProfile:
    """Objective value at each screened value of one parameter.

    A flat profile means the data do not identify that parameter; a sharp one
    means they do. This is reported rather than hidden behind the best fit.
    """

    parameter: str
    values: tuple[float, ...]
    distances: tuple[float, ...]

    @property
    def spread(self) -> float:
        return max(self.distances) - min(self.distances)


@dataclass(frozen=True)
class CalibrationFit:
    """Best fit, its distance, and what the data could and could not identify."""

    parameters: SimulationParameters
    distance: float
    profiles: tuple[ParameterProfile, ...]
    observed: ObservedProfile
    grid_size: int

    def simulate_profile(self, *, seed: int = 20261010) -> ObservedProfile:
        """Reproduce the fitted profile, for plotting observed against fitted."""
        return simulated_profile(self.parameters, self.observed, seed=seed)


def simulated_profile(
    parameters: SimulationParameters,
    template: ObservedProfile,
    *,
    seed: int = 20261010,
) -> ObservedProfile:
    """Run one group under `parameters` and summarise it like the real data."""
    settings = replace(
        parameters,
        n_animals=template.animals,
        days=template.days,
        interactions_per_animal_per_day=max(1, round(template.interactions_per_animal_day)),
        escape_probability_after_nonresponse=min(1.0, max(0.0, template.escape_rate)),
    )
    result = simulate_group("conventional", parameters=settings, seed=seed)
    days = daily_summary(result)
    return ObservedProfile(
        animals=template.animals,
        days=template.days,
        animal_days=sum(day.animal_days for day in days) or template.animal_days,
        interactions_per_animal_day=template.interactions_per_animal_day,
        escape_rate=template.escape_rate,
        pulses_per_animal_day=tuple(day.pulses_per_animal_day for day in days),
        audio_only_ratio=tuple(day.audio_only_response_ratio for day in days),
    )


def distance(
    observed: ObservedProfile,
    simulated: ObservedProfile,
    *,
    ratio_weight: float = 1.0,
) -> float:
    """Scale-free distance between two profiles, averaged over days.

    Pulse rates enter as relative error, so a profile with a mean of five pulses
    per animal-day is not automatically penalised more than one with a mean of
    one. The audio-only ratio is already a proportion.
    """
    if observed.days != simulated.days:
        raise ValueError("Profiles must cover the same number of days.")
    pulse_terms = [
        ((sim - obs) / obs) ** 2 if obs else (sim - obs) ** 2
        for obs, sim in zip(
            observed.pulses_per_animal_day, simulated.pulses_per_animal_day, strict=True
        )
    ]
    ratio_terms = [
        (sim - obs) ** 2
        for obs, sim in zip(observed.audio_only_ratio, simulated.audio_only_ratio, strict=True)
    ]
    return (fmean(pulse_terms) + ratio_weight * fmean(ratio_terms)) / (1.0 + ratio_weight)


def fit_parameters(
    observed: ObservedProfile,
    grid: CalibrationGrid | None = None,
    *,
    base: SimulationParameters | None = None,
) -> CalibrationFit:
    """Grid-search the behavioural parameters against an observed profile.

    Each grid point is simulated once per seed and averaged, because a single
    group is noisy. The returned fit includes the search size and the marginal
    profiles, so the report can say how much searching and how much identifying
    actually happened.
    """
    grid = grid or CalibrationGrid()
    base = base or SimulationParameters()
    points = grid.points()

    best: tuple[float, SimulationParameters] | None = None
    marginal: dict[str, dict[float, list[float]]] = {
        "learning_rate": {},
        "baseline_response_probability": {},
        "associative_response_weight": {},
        "social_response_weight": {},
    }

    for _index, candidate in enumerate(points):
        distances = [
            distance(
                observed,
                simulated_profile(candidate, observed, seed=seed),
                ratio_weight=grid.ratio_weight,
            )
            for seed in grid.seeds
        ]
        value = fmean(distances)
        if best is None or value < best[0]:
            best = (value, candidate)
        for name in marginal:
            marginal[name].setdefault(getattr(candidate, name), []).append(value)

    if best is None:  # pragma: no cover - points() already refuses an empty grid
        raise ValueError("No feasible parameter set was evaluated.")

    profiles = tuple(
        ParameterProfile(
            parameter=name,
            values=tuple(sorted(marginal[name])),
            distances=tuple(fmean(marginal[name][value]) for value in sorted(marginal[name])),
        )
        for name in marginal
    )
    return CalibrationFit(
        parameters=replace(base, **_as_settings(best[1])),  # type: ignore[arg-type]
        distance=best[0],
        profiles=profiles,
        observed=observed,
        grid_size=len(points),
    )


def _as_settings(candidate: SimulationParameters) -> dict[str, float]:
    return {
        "learning_rate": candidate.learning_rate,
        "baseline_response_probability": candidate.baseline_response_probability,
        "associative_response_weight": candidate.associative_response_weight,
        "social_response_weight": candidate.social_response_weight,
    }


def pseudo_data(
    parameters: SimulationParameters,
    *,
    animals: int = 5,
    days: int = 5,
    interactions_per_animal_per_day: int = 8,
    seed: int = 20261010,
) -> ObservedProfile:
    """Build a profile from the model itself, to test the pipeline without data."""
    template = ObservedProfile(
        animals=animals,
        days=days,
        animal_days=animals * days,
        interactions_per_animal_day=float(interactions_per_animal_per_day),
        escape_rate=parameters.escape_probability_after_nonresponse,
        pulses_per_animal_day=(0.0,) * days,
        audio_only_ratio=(0.0,) * days,
    )
    settings = replace(
        parameters,
        n_animals=animals,
        days=days,
        interactions_per_animal_per_day=interactions_per_animal_per_day,
    )
    result = simulate_group("conventional", parameters=settings, seed=seed)
    summaries = daily_summary(result)
    return replace(
        template,
        pulses_per_animal_day=tuple(day.pulses_per_animal_day for day in summaries),
        audio_only_ratio=tuple(day.audio_only_response_ratio for day in summaries),
    )


def format_calibration(fit: CalibrationFit) -> str:
    """Return a copyable report: the fit, its error, and its identifiability."""
    observed = fit.observed
    fitted = fit.simulate_profile()
    rows = [
        "CALIBRATED TO OBSERVED RECORDS - parameters remain estimates from a model, not measurements",
        f"observed: {observed.animals} animals, {observed.days} days, "
        f"{observed.animal_days} animal-days, "
        f"{observed.interactions_per_animal_day:.2f} interactions/animal-day (measured, not fitted)",
        f"grid points evaluated: {fit.grid_size}; best distance: {fit.distance:.5f}",
        "",
        "fitted parameters",
        f"  learning_rate={fit.parameters.learning_rate:.3f}",
        f"  baseline_response_probability={fit.parameters.baseline_response_probability:.3f}",
        f"  associative_response_weight={fit.parameters.associative_response_weight:.3f}",
        f"  social_response_weight={fit.parameters.social_response_weight:.3f}",
        "",
        "day | observed pulses/animal-day | fitted | observed audio-only | fitted",
        "--- | --- | --- | --- | ---",
    ]
    for index in range(observed.days):
        rows.append(
            f"{index + 1} | {observed.pulses_per_animal_day[index]:.3f} | "
            f"{fitted.pulses_per_animal_day[index]:.3f} | "
            f"{observed.audio_only_ratio[index]:.3f} | {fitted.audio_only_ratio[index]:.3f}"
        )
    rows.extend(
        [
            "",
            "identifiability (a flat profile means the data do not pin this parameter)",
            "parameter | best value | objective spread across its grid values",
            "--- | --- | ---",
        ]
    )
    for profile in fit.profiles:
        best_index = min(range(len(profile.distances)), key=profile.distances.__getitem__)
        rows.append(
            f"{profile.parameter} | {profile.values[best_index]:.3f} | {profile.spread:.5f}"
        )
    return "\n".join(rows)
