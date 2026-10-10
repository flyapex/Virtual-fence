from vf_training.power import PowerScenario, estimate_power, power_grid


def test_power_estimate_is_bounded_and_reproducible() -> None:
    scenario = PowerScenario(groups_per_arm=3, animals_per_group=3, tau=0.5, replications=8, seed=10)
    first = estimate_power(scenario)
    second = estimate_power(scenario)
    assert first == second
    assert 0.0 <= first.estimated_power <= 1.0


def test_power_grid_varies_transfer_assumption() -> None:
    results = power_grid(groups_per_arm=(3,), taus=(0.0, 1.0), replications=4, seed=5)
    assert [item.scenario.tau for item in results] == [0.0, 1.0]

