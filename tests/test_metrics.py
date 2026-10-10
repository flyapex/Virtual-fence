import pytest

from vf_training.metrics import (
    daily_summary,
    escape_count,
    group_pulse_rate,
    pulses_per_animal_per_day,
    success_ratio,
    time_to_criterion,
)
from vf_training.model import SimulationParameters, simulate_group


def test_metrics_match_event_counts() -> None:
    result = simulate_group("conventional", parameters=SimulationParameters(n_animals=2, days=2), seed=9)
    daily = pulses_per_animal_per_day(result)
    assert len(daily) == 4
    assert sum(item.pulses for item in daily) == sum(event.pulse_delivered for event in result.events)
    assert escape_count(result) == sum(event.escaped for event in result.events)
    assert 0.0 <= success_ratio(result) <= 1.0


def test_daily_summary_matches_event_counts_and_group_rate() -> None:
    result = simulate_group(
        "simulation",
        tau=0.6,
        parameters=SimulationParameters(n_animals=3, days=4),
        seed=11,
    )
    days = daily_summary(result)

    assert [day.day for day in days] == [1, 2, 3, 4]
    assert sum(day.interactions for day in days) == len(result.events)
    assert sum(day.pulses for day in days) == sum(event.pulse_delivered for event in result.events)
    assert sum(day.escapes for day in days) == escape_count(result)
    assert all(day.animal_days == 3 for day in days)
    # Transferred pre-training must be visible at the first boundary encounter.
    assert days[0].mean_associative_strength_before > 0.0
    assert 0.0 <= days[0].mean_response_probability <= 1.0
    assert 0.0 <= days[0].audio_only_response_ratio <= 1.0
    # The day-level rate must describe the same quantity as the group metric.
    assert days[0].pulses_per_animal_day == pytest.approx(group_pulse_rate(result, through_day=1))


def test_daily_summary_is_empty_without_events() -> None:
    assert daily_summary(()) == ()


def test_zero_transfer_arms_share_one_history_under_the_same_seed() -> None:
    """Characterises the model: no arm differs from conventional without tau.

    The simulation figure reports this overlap instead of drawing one line twice.
    """
    parameters = SimulationParameters(n_animals=2, days=3)
    conventional = simulate_group("conventional", parameters=parameters, seed=4)
    mock_boundary = simulate_group("mock_boundary", parameters=parameters, seed=4)

    assert daily_summary(conventional) == daily_summary(mock_boundary)


def test_time_to_criterion_is_none_when_unachieved() -> None:
    parameters = SimulationParameters(
        n_animals=1,
        days=2,
        interactions_per_animal_per_day=1,
        baseline_response_probability=0.0,
        associative_response_weight=0.0,
        social_response_weight=0.0,
    )
    result = simulate_group("conventional", parameters=parameters, seed=3)
    assert time_to_criterion(result, criterion=1.0, consecutive_days=2) is None

