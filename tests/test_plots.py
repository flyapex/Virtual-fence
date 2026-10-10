from pathlib import Path

import pytest

from vf_training.model import ARM_NAMES, SimulationParameters, simulate_group
from vf_training.plots import figure_path, plot_power_grid, plot_simulation
from vf_training.power import power_grid

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _requires_matplotlib() -> None:
    """Skip a rendering test when the optional plots extra is not installed."""
    pytest.importorskip("matplotlib", reason="figure rendering needs the optional plots extra")


def test_figure_path_builds_name_and_rejects_unknown_format(tmp_path: Path) -> None:
    assert figure_path(tmp_path, "power_grid", suffix="svg") == tmp_path / "power_grid.svg"
    assert figure_path(tmp_path, "power_grid", suffix=".PDF") == tmp_path / "power_grid.pdf"
    with pytest.raises(ValueError, match="Figure format must be one of"):
        figure_path(tmp_path, "power_grid", suffix="tiff")


def test_simulation_figure_is_written_for_one_arm(tmp_path: Path) -> None:
    _requires_matplotlib()
    result = simulate_group(
        "simulation", tau=0.6, parameters=SimulationParameters(n_animals=3, days=4), seed=7
    )
    target = figure_path(tmp_path, "one_arm", suffix="png")

    written = plot_simulation([result], path=target, dpi=72)

    assert written == target
    assert target.read_bytes().startswith(PNG_MAGIC)


def test_simulation_figure_overlays_three_arms_as_svg(tmp_path: Path) -> None:
    _requires_matplotlib()
    parameters = SimulationParameters(n_animals=2, days=3)
    results = [
        simulate_group(arm, tau=0.5 if arm == "simulation" else 0.0, parameters=parameters, seed=5)
        for arm in ARM_NAMES
    ]
    target = figure_path(tmp_path, "arms", suffix="svg")

    plot_simulation(results, path=target, dpi=72)

    assert "<svg" in target.read_text(encoding="utf-8")


def test_simulation_figure_requires_a_result() -> None:
    with pytest.raises(ValueError, match="At least one simulation result"):
        plot_simulation([], path="unused.png")


def test_power_figure_is_written_for_a_small_grid(tmp_path: Path) -> None:
    _requires_matplotlib()
    results = power_grid(
        groups_per_arm=(3, 4),
        taus=(0.0, 0.5),
        animals_per_group=2,
        replications=3,
        seed=1,
    )
    target = figure_path(tmp_path, "power", suffix="png")

    plot_power_grid(results, path=target, dpi=72)

    assert target.read_bytes().startswith(PNG_MAGIC)


def test_figure_output_directory_is_created(tmp_path: Path) -> None:
    _requires_matplotlib()
    result = simulate_group(
        "conventional", parameters=SimulationParameters(n_animals=1, days=2), seed=2
    )
    target = figure_path(tmp_path / "nested" / "results", "created", suffix="png")

    plot_simulation([result], path=target, dpi=72)

    assert target.is_file()
