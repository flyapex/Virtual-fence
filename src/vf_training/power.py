"""Group-level Monte Carlo power calculations for the primary planning contrast."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import combinations
from math import comb
import random
from statistics import fmean
from typing import Iterable

from .model import Arm, SimulationParameters, simulate_group_pulse_rate


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
        if self.groups_per_arm < 2 or self.animals_per_group < 1 or self.replications < 1:
            raise ValueError("Use at least two groups per arm, one animal per group, and one replication.")
        if not 0.0 <= self.tau <= 1.0:
            raise ValueError("tau must be between 0 and 1.")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1.")
        if self.primary_days < 1 or not 0.0 <= self.required_relative_reduction <= 1.0:
            raise ValueError("Invalid primary outcome window or required relative reduction.")


@dataclass(frozen=True)
class PowerResult:
    """Estimated rejection probability under a fully stated simulated scenario."""

    scenario: PowerScenario
    estimated_power: float
    successful_replications: int
    mean_relative_reduction: float
    mean_mock_relative_reduction: float


@lru_cache(maxsize=None)
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

    if total_partitions <= 50_000:
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
    for _ in range(10_000):
        rng.shuffle(values)
        if abs(fmean(values[:n_control]) - fmean(values[n_control:])) >= observed - 1e-12:
            exceedances += 1
    return (exceedances + 1) / 10_001


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
    scenario: PowerScenario = PowerScenario(),
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
    """
    scenario.validate()
    model_parameters = model_parameters or SimulationParameters()
    model_parameters.validate()
    rng = random.Random(scenario.seed)
    successes = 0
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
        if p_value < scenario.alpha and reduction >= scenario.required_relative_reduction:
            successes += 1
    return PowerResult(
        scenario=scenario,
        estimated_power=successes / scenario.replications,
        successful_replications=successes,
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
    """Return a compact, copyable table with no claim of empirical power."""
    rows = [
        "groups/arm | animals/group | tau | replications | estimated power | mean simulation reduction | mean mock reduction",
        "--- | --- | --- | --- | --- | --- | ---",
    ]
    for result in results:
        scenario = result.scenario
        rows.append(
            f"{scenario.groups_per_arm} | {scenario.animals_per_group} | {scenario.tau:.2f} | "
            f"{scenario.replications} | {result.estimated_power:.3f} | "
            f"{result.mean_relative_reduction:.3f} | {result.mean_mock_relative_reduction:.3f}"
        )
    return "\n".join(rows)

