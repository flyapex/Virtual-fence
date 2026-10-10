import random
from math import comb

import pytest

from vf_training.power import (
    EXACT_PARTITION_LIMIT,
    MONTE_CARLO_FLOOR,
    PowerScenario,
    _permutation_p_value,
    estimate_power,
    format_power_results,
    minimum_attainable_p,
    power_grid,
)


def test_exact_permutation_p_value_matches_enumeration() -> None:
    rng = random.Random(0)
    # Maximal separation at 3 vs 3: the extreme split and its mirror both count.
    assert _permutation_p_value([0.0, 0.0, 0.0], [1.0, 1.0, 1.0], rng) == pytest.approx(0.10)
    # Identical arms cannot be separated by any relabelling.
    assert _permutation_p_value([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], rng) == pytest.approx(1.0)
    assert _permutation_p_value([0.0] * 4, [1.0] * 4, rng) == pytest.approx(2 / 70)


def test_monte_carlo_branch_stays_above_its_add_one_floor() -> None:
    rng = random.Random(7)
    separated = _permutation_p_value([0.0] * 10, [1.0] * 10, rng)
    identical = _permutation_p_value([5.0] * 10, [5.0] * 10, rng)

    assert comb(20, 10) > EXACT_PARTITION_LIMIT  # this really is the other branch
    assert separated >= MONTE_CARLO_FLOOR
    assert identical == pytest.approx(1.0)


def test_minimum_attainable_p_follows_the_branch_in_use() -> None:
    assert minimum_attainable_p(PowerScenario(groups_per_arm=3)) == pytest.approx(0.10)
    assert minimum_attainable_p(PowerScenario(groups_per_arm=4)) == pytest.approx(2 / 70)
    # Above the exact limit the estimator changes, so the floor does too.
    assert minimum_attainable_p(PowerScenario(groups_per_arm=10)) == pytest.approx(
        MONTE_CARLO_FLOOR
    )


def test_three_groups_per_arm_is_required_by_the_design() -> None:
    with pytest.raises(ValueError, match="at least three groups per arm"):
        PowerScenario(groups_per_arm=2).validate()


def test_a_design_below_the_permutation_floor_cannot_succeed() -> None:
    scenario = PowerScenario(groups_per_arm=3, animals_per_group=3, tau=1.0, replications=6, seed=3)
    result = estimate_power(scenario)

    assert minimum_attainable_p(scenario) > scenario.alpha
    assert result.estimated_power == 0.0
    assert result.rejections == 0


def test_a_detectable_effect_produces_power_and_rejections() -> None:
    scenario = PowerScenario(
        groups_per_arm=4, animals_per_group=5, tau=1.0, replications=20, seed=11
    )
    result = estimate_power(scenario)

    assert result.estimated_power > 0.5
    assert result.rejections >= result.successful_replications
    assert result.rejection_rate == pytest.approx(result.rejections / 20)


def test_rejection_rate_separates_test_size_from_success() -> None:
    """At tau = 0 the reduction rule suppresses successes, not rejections."""
    scenario = PowerScenario(
        groups_per_arm=4, animals_per_group=5, tau=0.0, replications=40, seed=5
    )
    result = estimate_power(scenario)

    assert result.estimated_power == 0.0
    assert 0.0 <= result.rejection_rate <= 0.30


def test_table_marks_both_reasons_a_row_reads_zero() -> None:
    results = power_grid(
        groups_per_arm=(3, 4), taus=(0.0, 1.0), animals_per_group=3, replications=4, seed=9
    )
    table = format_power_results(results)

    assert "null by construction" in table
    assert "cannot reject at alpha" in table  # the 3-per-arm rows
    assert "below the 30% target" in table  # the 4-per-arm null-transfer row


def test_power_estimate_is_bounded_and_reproducible() -> None:
    scenario = PowerScenario(
        groups_per_arm=3, animals_per_group=3, tau=0.5, replications=8, seed=10
    )
    first = estimate_power(scenario)
    second = estimate_power(scenario)

    assert first == second
    assert 0.0 <= first.estimated_power <= 1.0


def test_power_grid_varies_transfer_assumption() -> None:
    results = power_grid(groups_per_arm=(3,), taus=(0.0, 1.0), replications=4, seed=5)

    assert [item.scenario.tau for item in results] == [0.0, 1.0]
