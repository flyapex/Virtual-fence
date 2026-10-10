from vf_training.metrics import escape_count, pulses_per_animal_per_day, success_ratio, time_to_criterion
from vf_training.model import SimulationParameters, simulate_group


def test_metrics_match_event_counts() -> None:
    result = simulate_group("conventional", parameters=SimulationParameters(n_animals=2, days=2), seed=9)
    daily = pulses_per_animal_per_day(result)
    assert len(daily) == 4
    assert sum(item.pulses for item in daily) == sum(event.pulse_delivered for event in result.events)
    assert escape_count(result) == sum(event.escaped for event in result.events)
    assert 0.0 <= success_ratio(result) <= 1.0


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

