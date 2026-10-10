"""Morris screening of the behavioural assumptions.

Every parameter screened here is an unmeasured assumption. Screening answers a
narrow, answerable question: which assumptions actually move the planning answer,
so that calibration and elicitation effort goes where it matters. It reports
elementary effects, which are sensitivity measures, not causal claims and not
parameter estimates.

The method is the Morris one-at-a-time trajectory design (Morris 1991): each
trajectory perturbs one assumption at a time along a random path through a
discretised grid, and the elementary effects are summarised by their mean
(`mu`, signed), mean absolute value (`mu_star`, influence) and standard deviation
(`sigma`, non-linearity or interaction).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from math import sqrt

from .model import SimulationParameters, simulate_group_pulse_rate

#: Plausible screening ranges. They are assumptions about assumptions, chosen so
#: that every combination stays a valid probability model: the three response
#: components can sum to one, but never above it.
ASSUMPTION_RANGES: tuple[tuple[str, float, float, str], ...] = (
    ("learning_rate", 0.10, 0.40, "Rescorla-Wagner alpha: how fast a pulse teaches"),
    ("baseline_response_probability", 0.00, 0.10, "response with no learning and no social cue"),
    ("associative_response_weight", 0.40, 0.70, "weight on the learned association"),
    ("social_response_weight", 0.00, 0.20, "weight on recent group responses"),
    ("escape_probability_after_nonresponse", 0.00, 0.10, "escape given a pulse"),
    ("interactions_per_animal_per_day", 4.0, 16.0, "boundary meetings per animal-day"),
    ("tau", 0.00, 1.00, "transfer of pre-trained association to the real context"),
)

INTEGER_ASSUMPTIONS = ("interactions_per_animal_per_day",)
ASSUMPTION_NAMES = tuple(name for name, _low, _high, _note in ASSUMPTION_RANGES)
_BOUNDS = {name: (low, high) for name, low, high, _note in ASSUMPTION_RANGES}
_NOTES = {name: note for name, _low, _high, note in ASSUMPTION_RANGES}


@dataclass(frozen=True)
class ScreeningDesign:
    """Sampling effort and the trial shape the reduction is computed for."""

    groups_per_arm: int = 4
    animals_per_group: int = 5
    internal_replications: int = 10
    trajectories: int = 8
    grid_levels: int = 4
    primary_days: int = 3
    seed: int = 20261010
    base: SimulationParameters = field(default_factory=SimulationParameters)

    def validate(self) -> None:
        if self.groups_per_arm < 3:
            raise ValueError("Screening uses the design's minimum of three groups per arm.")
        if self.animals_per_group < 1 or self.internal_replications < 1:
            raise ValueError("animals_per_group and internal_replications must be positive.")
        if self.trajectories < 2:
            raise ValueError("Use at least two trajectories so sigma is defined.")
        if self.grid_levels < 2:
            raise ValueError("Use at least two grid levels.")


@dataclass(frozen=True)
class ElementaryEffect:
    """One normalised perturbation of one assumption along one trajectory."""

    parameter: str
    trajectory: int
    effect: float


@dataclass(frozen=True)
class ScreeningResult:
    """Summary of one assumption's elementary effects across trajectories."""

    parameter: str
    mu: float
    mu_star: float
    sigma: float
    low_value: float
    high_value: float
    note: str


def _value_from_unit(name: str, unit: float) -> float:
    low, high = _BOUNDS[name]
    value = low + unit * (high - low)
    if name in INTEGER_ASSUMPTIONS:
        return float(round(value))
    return value


def _parameters_for(
    assignment: Mapping[str, float], base: SimulationParameters
) -> SimulationParameters:
    """Apply one assignment of assumption values on top of the base parameters."""
    settings: dict[str, float | int] = {}
    for name, value in assignment.items():
        if name == "tau" or name not in ASSUMPTION_NAMES:
            continue
        settings[name] = round(value) if name in INTEGER_ASSUMPTIONS else value
    parameters = replace(base, **settings)  # type: ignore[arg-type]
    parameters.validate()
    return parameters


def mean_relative_reduction(
    assignment: Mapping[str, float],
    *,
    design: ScreeningDesign,
    rng: random.Random,
) -> float:
    """Primary screening target: mean reduction in pulses per animal-day.

    This is the quantity the study is planned around, computed for the assumed
    design without running the permutation test, so it stays cheap enough for
    hundreds of evaluations. It is a simulated quantity under assumptions.
    """
    parameters = _parameters_for(assignment, design.base)
    tau = float(assignment.get("tau", 0.0))
    parameters = replace(parameters, n_animals=design.animals_per_group, days=design.primary_days)
    reductions: list[float] = []
    for _ in range(design.internal_replications):
        conventional = simulate_group_pulse_rate(
            "conventional",
            parameters=parameters,
            seed=rng.randrange(0, 2**31),
        )
        trained = simulate_group_pulse_rate(
            "simulation",
            tau=tau,
            parameters=parameters,
            seed=rng.randrange(0, 2**31),
        )
        if conventional:
            reductions.append((conventional - trained) / conventional)
    return sum(reductions) / len(reductions) if reductions else 0.0


def _unit_trajectory(
    rng: random.Random, names: Sequence[str], levels: int
) -> list[dict[str, float]]:
    """Build one Morris path: a base point, then one step per assumption."""
    step = levels / (2.0 * (levels - 1))
    span = 1.0 / (levels - 1)
    walk: list[dict[str, float]] = []
    point: dict[str, float] = {}
    directions: dict[str, float] = {}
    for name in names:
        direction = rng.choice((1.0, -1.0))
        directions[name] = direction
        if direction > 0:
            # A positive step must stay inside [0, 1], so the base is in the lower half.
            choices = [index * span for index in range(levels // 2)]
        else:
            choices = [index * span for index in range(levels // 2, levels)]
        point[name] = rng.choice(choices)
    walk.append(dict(point))
    order = list(names)
    rng.shuffle(order)
    for name in order:
        point[name] = round(point[name] + directions[name] * step, 10)
        walk.append(dict(point))
    return walk


def elementary_effects(
    target: Callable[[Mapping[str, float]], float],
    *,
    design: ScreeningDesign,
    names: Sequence[str] = ASSUMPTION_NAMES,
) -> tuple[ElementaryEffect, ...]:
    """Run the Morris trajectories over `target` and return the raw effects.

    `target` is injected so the screening itself can be tested without the model.
    """
    design.validate()
    rng = random.Random(design.seed)
    effects: list[ElementaryEffect] = []
    for trajectory in range(design.trajectories):
        walk = _unit_trajectory(rng, names, design.grid_levels)
        values = [
            target({name: _value_from_unit(name, unit) for name, unit in point.items()})
            for point in walk
        ]
        for position in range(1, len(walk)):
            changed = [name for name in names if walk[position][name] != walk[position - 1][name]]
            if len(changed) != 1:
                raise AssertionError("A Morris step must change exactly one assumption.")
            name = changed[0]
            difference = walk[position][name] - walk[position - 1][name]
            effects.append(
                ElementaryEffect(
                    parameter=name,
                    trajectory=trajectory,
                    effect=(values[position] - values[position - 1]) / difference,
                )
            )
    return tuple(effects)


def summarise(effects: Sequence[ElementaryEffect]) -> tuple[ScreeningResult, ...]:
    """Summarise elementary effects per assumption, ordered by influence."""
    grouped: dict[str, list[float]] = {}
    for effect in effects:
        grouped.setdefault(effect.parameter, []).append(effect.effect)

    summaries: list[ScreeningResult] = []
    for name, values in grouped.items():
        count = len(values)
        mean = sum(values) / count
        mean_absolute = sum(abs(value) for value in values) / count
        variance = sum((value - mean) ** 2 for value in values) / (count - 1) if count > 1 else 0.0
        low, high = _BOUNDS[name]
        summaries.append(
            ScreeningResult(
                parameter=name,
                mu=mean,
                mu_star=mean_absolute,
                sigma=sqrt(variance),
                low_value=low,
                high_value=high,
                note=_NOTES[name],
            )
        )
    return tuple(sorted(summaries, key=lambda item: item.mu_star, reverse=True))


def morris_screening(
    design: ScreeningDesign | None = None,
    *,
    target: Callable[[Mapping[str, float]], float] | None = None,
) -> tuple[ScreeningResult, ...]:
    """Screen the behavioural assumptions against the planned design."""
    design = design or ScreeningDesign()
    design.validate()
    rng = random.Random(design.seed)

    def model_target(assignment: Mapping[str, float]) -> float:
        return mean_relative_reduction(assignment, design=design, rng=rng)

    effects = elementary_effects(target or model_target, design=design)
    return summarise(effects)


def format_screening(results: Sequence[ScreeningResult]) -> str:
    """Return a compact, copyable table of screening results.

    `mu_star` is influence on the mean pulse reduction; `sigma` is how much that
    influence changes along different paths, which is where non-linearity or
    interaction between assumptions shows up. Both are in reduction units per
    full-range change of the assumption.
    """
    rows = [
        "assumption | mu | mu_star (influence) | sigma (non-linearity) | screened range | note",
        "--- | --- | --- | --- | --- | ---",
    ]
    for result in results:
        rows.append(
            f"{result.parameter} | {result.mu:+.3f} | {result.mu_star:.3f} | {result.sigma:.3f} | "
            f"{result.low_value:g} to {result.high_value:g} | {result.note}"
        )
    return "\n".join(rows)
