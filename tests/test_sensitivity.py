"""Tests for the Morris screening of assumed parameters."""

import random
from collections.abc import Mapping
from pathlib import Path

import pytest

from vf_training.model import SimulationParameters
from vf_training.plots import plot_screening
from vf_training.sensitivity import (
    ASSUMPTION_NAMES,
    ASSUMPTION_RANGES,
    ScreeningDesign,
    elementary_effects,
    format_screening,
    mean_relative_reduction,
    morris_screening,
    summarise,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _tiny_design(**overrides: object) -> ScreeningDesign:
    settings: dict[str, object] = {
        "trajectories": 2,
        "internal_replications": 1,
        "animals_per_group": 2,
    }
    settings.update(overrides)
    return ScreeningDesign(**settings)  # type: ignore[arg-type]


def test_ranges_keep_every_combination_a_valid_model() -> None:
    """The three response components may sum to one, never above it."""
    bounds = {name: (low, high) for name, low, high, _note in ASSUMPTION_RANGES}
    parameters = SimulationParameters(
        baseline_response_probability=bounds["baseline_response_probability"][1],
        associative_response_weight=bounds["associative_response_weight"][1],
        social_response_weight=bounds["social_response_weight"][1],
    )

    parameters.validate()  # must not raise

    total = (
        parameters.baseline_response_probability
        + parameters.associative_response_weight
        + parameters.social_response_weight
    )
    assert total <= 1.0


def test_screening_recovers_a_linear_target_exactly() -> None:
    """On a linear target the effect is the coefficient times the screened range.

    Morris effects are normalised: they are the change in the target per full
    range of the assumption, which is what makes parameters on different scales
    comparable in one table.
    """

    def target(assignment: Mapping[str, float]) -> float:
        return 2.0 * assignment["learning_rate"] + 1.0 * assignment["tau"]

    design = ScreeningDesign(trajectories=4, grid_levels=4, seed=1)
    effects = elementary_effects(target, design=design, names=("learning_rate", "tau"))
    results = {item.parameter: item for item in summarise(effects)}

    # learning_rate spans 0.10 to 0.40, tau spans 0 to 1.
    assert results["learning_rate"].mu == pytest.approx(2.0 * 0.30)
    assert results["tau"].mu == pytest.approx(1.0)
    assert results["learning_rate"].sigma == pytest.approx(0.0, abs=1e-9)


def test_every_step_changes_exactly_one_assumption() -> None:
    seen: list[int] = []

    def counting_target(assignment: Mapping[str, float]) -> float:
        seen.append(len(assignment))
        return sum(assignment.values())

    design = ScreeningDesign(trajectories=3, grid_levels=4, seed=5)
    effects = elementary_effects(counting_target, design=design)

    # One base point plus one step per assumption, for every trajectory.
    assert len(seen) == design.trajectories * (len(ASSUMPTION_NAMES) + 1)
    assert len(effects) == design.trajectories * len(ASSUMPTION_NAMES)


def test_model_screening_is_reproducible_and_complete() -> None:
    design = _tiny_design(trajectories=3)

    first = morris_screening(design)
    second = morris_screening(design)

    assert first == second
    assert {item.parameter for item in first} == set(ASSUMPTION_NAMES)
    assert all(item.mu_star >= 0.0 for item in first)
    assert all(item.sigma >= 0.0 for item in first)
    # Ordered by influence, so the figure and the table agree.
    assert [item.mu_star for item in first] == sorted(
        (item.mu_star for item in first), reverse=True
    )


def test_the_design_minimum_is_enforced() -> None:
    with pytest.raises(ValueError, match="three groups per arm"):
        ScreeningDesign(groups_per_arm=2).validate()
    with pytest.raises(ValueError, match="at least two trajectories"):
        ScreeningDesign(trajectories=1).validate()
    with pytest.raises(ValueError, match="grid levels"):
        ScreeningDesign(grid_levels=1).validate()


def test_reduction_target_responds_to_transfer() -> None:
    """A fully transferred association must beat no transfer at all."""
    design = ScreeningDesign(internal_replications=6, animals_per_group=3)
    without = mean_relative_reduction({"tau": 0.0}, design=design, rng=random.Random(0))
    with_transfer = mean_relative_reduction({"tau": 1.0}, design=design, rng=random.Random(0))

    assert with_transfer > without


def test_table_lists_every_assumption_and_disclaims_itself() -> None:
    table = format_screening(morris_screening(_tiny_design()))

    assert "mu_star (influence)" in table
    for name in ASSUMPTION_NAMES:
        assert name in table


def test_screening_figure_renders(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib", reason="figure rendering needs the optional plots extra")

    target = plot_screening(
        morris_screening(_tiny_design()), path=tmp_path / "screening.png", dpi=60
    )

    assert target.read_bytes().startswith(PNG_MAGIC)


def test_screening_figure_requires_a_result() -> None:
    with pytest.raises(ValueError, match="At least one screening result"):
        plot_screening([], path="unused.png")
