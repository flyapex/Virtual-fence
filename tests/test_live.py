"""Tests for the adjustable live playback controls."""

from pathlib import Path

import pytest

from vf_training.live import (
    ANIMAL_RANGE,
    DAY_RANGE,
    LiveControls,
    LivePlayback,
    display_available,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _requires_matplotlib() -> None:
    pytest.importorskip("matplotlib", reason="the live view needs the optional plots extra")


def test_controls_validate_their_ranges() -> None:
    LiveControls().validate()

    with pytest.raises(ValueError, match="animals must be within"):
        LiveControls(animals=ANIMAL_RANGE[1] + 1).validate()
    with pytest.raises(ValueError, match="days must be within"):
        LiveControls(days=DAY_RANGE[1] + 1).validate()
    with pytest.raises(ValueError, match="tau must be between"):
        LiveControls(tau=1.5).validate()
    with pytest.raises(ValueError, match="learning_rate must be within"):
        LiveControls(learning_rate=0.9).validate()
    with pytest.raises(ValueError, match="arm must be one of"):
        LiveControls(arm="unknown").validate()  # type: ignore[arg-type]


def test_controls_define_the_simulated_group() -> None:
    controls = LiveControls(arm="simulation", tau=0.8, animals=7, days=2, seed=99)
    result = controls.simulate()

    assert len(result.final_associative_strengths) == 7
    assert {event.day for event in result.events} == {1, 2}
    assert result.tau == pytest.approx(0.8)
    # Deterministic for a fixed seed, so a viewer can re-run exactly what they saw.
    assert controls.simulate() == result


def test_tau_only_applies_to_the_simulation_arm() -> None:
    assert LiveControls(arm="conventional", tau=0.9).simulate().tau == 0.0
    assert LiveControls(arm="mock_boundary", tau=0.9).simulate().tau == 0.0


def test_changing_the_animal_control_changes_the_group() -> None:
    few = LiveControls(animals=2, days=1).simulate()
    many = LiveControls(animals=8, days=1).simulate()

    assert len(few.final_associative_strengths) == 2
    assert len(many.final_associative_strengths) == 8


def test_live_preview_renders_the_field_and_its_controls(tmp_path: Path) -> None:
    _requires_matplotlib()
    view = LivePlayback(LiveControls(animals=4, days=1, show_strength=True), dpi=60)

    target = view.save_preview(tmp_path / "live.png", frame_index=2)

    assert target.read_bytes().startswith(PNG_MAGIC)
    assert target.stat().st_size > 20_000  # the field and the control column are drawn


def test_preview_rejects_an_unsupported_format(tmp_path: Path) -> None:
    _requires_matplotlib()
    view = LivePlayback(LiveControls(animals=2, days=1), dpi=60)

    with pytest.raises(ValueError, match="preview must end with"):
        view.save_preview(tmp_path / "live.bmp")


@pytest.mark.skipif(not display_available(), reason="needs an interactive display")
def test_live_animation_ticks_without_opening_a_window() -> None:
    _requires_matplotlib()
    view = LivePlayback(LiveControls(animals=3, days=1), dpi=60)

    view.start(show=False)

    assert view.animation is not None
    assert view._tick(0)  # one frame produces artists to redraw
    view.figure.canvas.draw()
    view.timer.stop()
    view.plt.close(view.figure)
