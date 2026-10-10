"""Group-level Monte Carlo power calculations for the primary planning contrast."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, replace
from functools import cache
from itertools import combinations
from math import comb
from statistics import fmean

from .model import Arm, SimulationParameters, simulate_group_pulse_rate

#: Partition count at or below which the permutation test is enumerated exactly.
EXACT_PARTITION_LIMIT = 50_000
#: Relabellings used by the Monte Carlo branch above that limit.
MONTE_CARLO_DRAWS = 10_000
#: Smallest p the Monte Carlo branch can return, from its add-one estimator.
MONTE_CARLO_FLOOR = 1 / (MONTE_CARLO_DRAWS + 1)


@dataclass(frozen=True)
class PowerScenario:
    """Unmeasured planning assumptions for the group-level power calculation."""

    groups_per_arm: int = 3
    animals_per_group: int = 5
    tau: float = 0.50
    replications: int = 500
    alpha: float = 0.05
    primary_days: int = 3
    required_relative_reduction: float = 0.30
    seed: int = 20261010

    def validate(self) -> None:
        if self.groups_per_arm < 3 or self.animals_per_group < 1 or self.replications < 1:
            raise ValueError(
                "Use at least three groups per arm, as the study design requires, "
                "one animal per group, and one replication."
            )
        if not 0.0 <= self.tau <= 1.0:
            raise ValueError("tau must be between 0 and 1.")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1.")
        if self.primary_days < 1 or not 0.0 <= self.required_relative_reduction <= 1.0:
            raise ValueError("Invalid primary outcome window or required relative reduction.")


@dataclass(frozen=True)
class PowerResult:
    """Probability of a *successful simulated trial* under a stated scenario.

    `estimated_power` counts only replications where the permutation test
    rejected **and** the observed reduction reached
    `required_relative_reduction`. It is therefore neither the test's size nor
    conventional power. `rejections` counts the first condition alone, so at
    `tau = 0` its rate estimates the achieved size of the test under the null.
    """

    scenario: PowerScenario
    estimated_power: float
    successful_replications: int
    rejections: int
    mean_relative_reduction: float
    mean_mock_relative_reduction: float

    @property
    def rejection_rate(self) -> float:
        """Rejections at alpha, before the reduction requirement is applied."""
        return self.rejections / self.scenario.replications


@cache
def _partitions(total_count: int, left_count: int) -> tuple[tuple[int, ...], ...]:
    """Cache exact group-label partitions used repeatedly in a power grid."""
    return tuple(combinations(range(total_count), left_count))


def _permutation_p_value(
    conventional: Iterable[float], simulation: Iterable[float], rng: random.Random
) -> float:
    """Two-sided group-label permutation p-value without a statistics dependency."""
    control = tuple(conventional)
    trained = tuple(simulation)
    n_control = len(control)
    pooled = control + trained
    observed = abs(fmean(control) - fmean(trained))
    total_partitions = comb(len(pooled), n_control)

    if total_partitions <= EXACT_PARTITION_LIMIT:
        exceedances = 0
        pooled_sum = sum(pooled)
        n_trained = len(trained)
        for chosen_indices in _partitions(len(pooled), n_control):
            left_sum = sum(pooled[index] for index in chosen_indices)
            difference = abs(left_sum / n_control - (pooled_sum - left_sum) / n_trained)
            if difference >= observed - 1e-12:
                exceedances += 1
        return exceedances / total_partitions

    # ASSUMPTION: 10,000 random relabellings are adequate for large planning grids.
    exceedances = 0
    values = list(pooled)
    for _ in range(MONTE_CARLO_DRAWS):
        rng.shuffle(values)
        if abs(fmean(values[:n_control]) - fmean(values[n_control:])) >= observed - 1e-12:
            exceedances += 1
    return (exceedances + 1) / (MONTE_CARLO_DRAWS + 1)


def _simulate_arm_outcomes(
    arm: Arm,
    scenario: PowerScenario,
    model_parameters: SimulationParameters,
    rng: random.Random,
) -> tuple[float, ...]:
    """Generate one independent group-level primary outcome per group."""
    parameters = replace(
        model_parameters,
        n_animals=scenario.animals_per_group,
        # Later days cannot affect the first-three-day primary outcome, so do
        # not simulate them in this calculation.
        days=scenario.primary_days,
    )
    tau = scenario.tau if arm == "simulation" else 0.0
    outcomes: list[float] = []
    for group_number in range(1, scenario.groups_per_arm + 1):
        outcomes.append(
            simulate_group_pulse_rate(
                arm,
                tau=tau,
                parameters=parameters,
                group_id=f"{arm}-{group_number}",
                seed=rng.randrange(0, 2**31),
            )
        )
    return tuple(outcomes)


def estimate_power(
    scenario: PowerScenario | None = None,
    *,
    model_parameters: SimulationParameters | None = None,
) -> PowerResult:
    """Estimate primary-contrast power with group as the analysis unit.

    Each Monte Carlo replication simulates distinct conventional, pre-trained,
    and mock-boundary groups. The primary contrast remains pre-training versus
    conventional. It counts success only if a two-sided group-label permutation
    test is below `alpha` *and* simulated pre-training clears the prespecified
    30% (default) pulse-reduction threshold. Therefore the result is conditional
    on all behavioural assumptions in `model_parameters` and `scenario`.

    A missing `scenario` uses the module defaults, built on each call rather
    than shared between calls.
    """
    scenario = scenario or PowerScenario()
    scenario.validate()
    model_parameters = model_parameters or SimulationParameters()
    model_parameters.validate()
    rng = random.Random(scenario.seed)
    successes = 0
    rejections = 0
    relative_reductions: list[float] = []
    mock_relative_reductions: list[float] = []
    for _ in range(scenario.replications):
        conventional = _simulate_arm_outcomes("conventional", scenario, model_parameters, rng)
        simulation = _simulate_arm_outcomes("simulation", scenario, model_parameters, rng)
        mock_boundary = _simulate_arm_outcomes("mock_boundary", scenario, model_parameters, rng)
        control_mean = fmean(conventional)
        trained_mean = fmean(simulation)
        reduction = (control_mean - trained_mean) / control_mean if control_mean else 0.0
        relative_reductions.append(reduction)
        mock_relative_reductions.append(
            (control_mean - fmean(mock_boundary)) / control_mean if control_mean else 0.0
        )
        p_value = _permutation_p_value(conventional, simulation, rng)
        if p_value < scenario.alpha:
            rejections += 1
            if reduction >= scenario.required_relative_reduction:
                successes += 1
    return PowerResult(
        scenario=scenario,
        estimated_power=successes / scenario.replications,
        successful_replications=successes,
        rejections=rejections,
        mean_relative_reduction=fmean(relative_reductions),
        mean_mock_relative_reduction=fmean(mock_relative_reductions),
    )


def power_grid(
    *,
    groups_per_arm: Iterable[int] = (3, 4, 5, 6),
    taus: Iterable[float] = (0.0, 0.25, 0.50, 0.75, 1.0),
    animals_per_group: int = 5,
    replications: int = 500,
    seed: int = 20261010,
    model_parameters: SimulationParameters | None = None,
) -> tuple[PowerResult, ...]:
    """Run a labelled planning grid across replication and transfer assumptions."""
    results: list[PowerResult] = []
    for group_count in groups_per_arm:
        for tau_index, tau in enumerate(taus):
            scenario = PowerScenario(
                groups_per_arm=group_count,
                animals_per_group=animals_per_group,
                tau=tau,
                replications=replications,
                seed=seed + 10_000 * group_count + tau_index,
            )
            results.append(estimate_power(scenario, model_parameters=model_parameters))
    return tuple(results)


def format_power_results(results: Iterable[PowerResult]) -> str:
    """Return a compact, copyable table with no claim of empirical power.

    Four things keep the numbers from being read as findings. The power column
    is successful-trial power, not the test's size; `rejection rate` reports the
    test alone. `mean mock reduction` is a null by construction, because the
    mock-boundary arm is simulated with the conventional mechanism. The `note`
    column separates the two reasons a row can read zero: a design floor at or
    above alpha, where no effect of any size could reject, and a mean reduction
    below the target, where the simulated effect itself is too small.
    """
    rows = [
        "groups/arm | animals/group | tau | replications | successful-trial power | "
        "rejection rate (p<alpha only) | mean simulation reduction | "
        "mean mock reduction (null by construction) | note",
        "--- | --- | --- | --- | --- | --- | --- | --- | ---",
    ]
    for result in results:
        scenario = result.scenario
        floor = minimum_attainable_p(scenario)
        notes: list[str] = []
        if floor >= scenario.alpha:
            notes.append(
                f"design floor min p={floor:.3f} cannot reject at alpha; "
                "this row cannot speak to effect size"
            )
        elif (
            result.successful_replications == 0
            and result.mean_relative_reduction < scenario.required_relative_reduction
        ):
            notes.append(
                f"mean reduction {result.mean_relative_reduction:.3f} is below the "
                f"{scenario.required_relative_reduction:.0%} target"
            )
        rows.append(
            f"{scenario.groups_per_arm} | {scenario.animals_per_group} | {scenario.tau:.2f} | "
            f"{scenario.replications} | {result.estimated_power:.3f} | "
            f"{result.rejection_rate:.3f} | {result.mean_relative_reduction:.3f} | "
            f"{result.mean_mock_relative_reduction:.3f} | {'; '.join(notes)}"
        )
    return "\n".join(rows)


def minimum_attainable_p(scenario: PowerScenario) -> float:
    """Return the smallest two-sided permutation p this design can produce.

    With g groups per arm the pooled sample holds 2g groups, and the most
    extreme split and its mirror image both reach the observed difference, so the
    exact branch cannot go below 2 / C(2g, g). Above the exact partition limit
    the add-one Monte Carlo estimator takes over, with a higher floor of
    1 / (draws + 1). A design whose floor is at or above `alpha` cannot reject
    whatever the data show, so a power estimate of zero for it is arithmetic
    rather than evidence about the intervention.
    """
    total_partitions = comb(2 * scenario.groups_per_arm, scenario.groups_per_arm)
    if total_partitions <= EXACT_PARTITION_LIMIT:
        return 2.0 / total_partitions
    return MONTE_CARLO_FLOOR
