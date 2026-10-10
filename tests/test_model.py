from vf_training.metrics import group_pulse_rate
from vf_training.model import (
    SimulationParameters,
    initial_associative_strength,
    simulate_group,
    simulate_group_pulse_rate,
)


def test_simulation_transfer_sets_higher_initial_association() -> None:
    parameters = SimulationParameters(simulated_pretraining_trials=8)
    assert initial_associative_strength("simulation", 0.5, parameters) > 0.0
    assert initial_associative_strength("conventional", 0.0, parameters) == 0.0
    assert initial_associative_strength("mock_boundary", 0.0, parameters) == 0.0


def test_pulse_updates_associative_strength() -> None:
    parameters = SimulationParameters(
        n_animals=1,
        days=1,
        interactions_per_animal_per_day=1,
        baseline_response_probability=0.0,
        associative_response_weight=0.0,
        social_response_weight=0.0,
        escape_probability_after_nonresponse=0.0,
    )
    result = simulate_group("conventional", parameters=parameters, seed=1)
    event = result.events[0]
    assert event.pulse_delivered is True
    assert event.associative_strength_after > event.associative_strength_before


def test_simulation_is_reproducible_with_fixed_seed() -> None:
    first = simulate_group("simulation", tau=0.6, seed=44)
    second = simulate_group("simulation", tau=0.6, seed=44)
    assert first == second


def test_fast_pulse_rate_matches_recorded_history() -> None:
    parameters = SimulationParameters(days=3)
    recorded = simulate_group("simulation", tau=0.6, parameters=parameters, seed=44)
    fast_rate = simulate_group_pulse_rate("simulation", tau=0.6, parameters=parameters, seed=44)
    assert fast_rate == group_pulse_rate(recorded, through_day=3)

