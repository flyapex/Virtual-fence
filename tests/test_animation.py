from pathlib import Path
from typing import Any

import pytest

from vf_training.animation import (
    APPROACH_X,
    FENCE_X,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    animate_simulation,
    animation_frames,
    home_positions,
)
from vf_training.model import SimulationParameters, SimulationResult, simulate_group

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _small_result(**overrides: Any) -> SimulationResult:
    parameters = SimulationParameters(n_animals=3, days=2, **overrides)
    return simulate_group("simulation", tau=0.6, parameters=parameters, seed=13)


def _requires_matplotlib() -> None:
    pytest.importorskip("matplotlib", reason="animation needs the optional plots extra")


def test_home_positions_stay_inside_the_field() -> None:
    homes = home_positions(5)

    assert len(homes) == 5
    assert all(0.0 < x < APPROACH_X and 0.0 < y < FIELD_HEIGHT for x, y in homes)
    with pytest.raises(ValueError, match="At least one animal"):
        home_positions(0)


def test_frames_expand_every_interaction_and_count_pulses() -> None:
    result = _small_result()
    frames = animation_frames(result, steps_per_interaction=4)

    assert len(frames) == len(result.events) * 4
    assert [frame.interaction_number for frame in frames] == [
        event.interaction_number for event in result.events for _ in range(4)
    ]

    pulses = responses = escapes = 0
    counted: set[int] = set()
    for frame in frames:
        if frame.interaction_number not in counted:
            counted.add(frame.interaction_number)
            pulses += int(frame.event.pulse_delivered)
            responses += int(frame.event.audio_only_response)
            escapes += int(frame.event.escaped)
        assert frame.pulses_so_far == pulses
        assert frame.responses_so_far == responses
        assert frame.escapes_so_far == escapes


def test_decision_frames_show_the_right_outcome_at_the_fence() -> None:
    result = _small_result()
    frames = animation_frames(result, steps_per_interaction=5)
    seen_pulse = seen_response = False

    for frame in frames:
        actor = frame.event.animal_id
        pose = frame.animals[actor]
        if pose.state == "pulse":
            seen_pulse = True
            assert frame.event.pulse_delivered
            assert pose.x >= FENCE_X
            # the pulse lands on this frame, so the strength is already updated
            assert pose.strength == pytest.approx(frame.event.associative_strength_after)
        if pose.state == "audio_response":
            seen_response = True
            assert frame.event.audio_only_response
            assert pose.x < APPROACH_X
        if pose.state == "escaped":
            assert frame.event.escaped
            assert pose.x > FENCE_X

    assert seen_pulse
    assert seen_response


def test_every_pose_stays_inside_the_drawn_field() -> None:
    result = _small_result()
    for frame in animation_frames(result, steps_per_interaction=3):
        for pose in frame.animals:
            assert -0.5 <= pose.x <= FIELD_WIDTH
            assert 0.0 <= pose.y <= FIELD_HEIGHT
            assert 0.0 <= pose.strength <= 1.0


def test_frames_reject_an_empty_or_too_coarse_animation() -> None:
    empty = SimulationResult(
        group_id="group-1",
        arm="conventional",
        tau=0.0,
        events=(),
        final_associative_strengths=(0.0,),
    )
    with pytest.raises(ValueError, match="no boundary interactions"):
        animation_frames(empty)
    with pytest.raises(ValueError, match="at least three steps"):
        animation_frames(_small_result(), steps_per_interaction=2)


def test_gif_and_still_export_write_real_files(tmp_path: Path) -> None:
    _requires_matplotlib()
    # Deliberately tiny: this exercises the full export path, not a long run.
    result = simulate_group(
        "simulation",
        tau=0.6,
        parameters=SimulationParameters(n_animals=2, days=1, interactions_per_animal_per_day=2),
        seed=3,
    )

    gif = animate_simulation(
        result, steps_per_interaction=3, interval_ms=100, dpi=60, save=tmp_path / "play.gif"
    )
    still = animate_simulation(
        result, steps_per_interaction=3, dpi=60, still=tmp_path / "frame.png", still_at=0.9
    )

    assert gif is not None
    assert gif.read_bytes()[:4] == b"GIF8"
    assert still is not None
    assert still.read_bytes().startswith(PNG_MAGIC)


def test_export_options_are_validated(tmp_path: Path) -> None:
    result = _small_result()
    with pytest.raises(ValueError, match=r"writes \.gif"):
        animate_simulation(result, save=tmp_path / "play.mp4")
    with pytest.raises(ValueError, match="either save or still"):
        animate_simulation(result, save=tmp_path / "a.gif", still=tmp_path / "b.png")
    with pytest.raises(ValueError, match="still_at must be between"):
        animate_simulation(result, still=tmp_path / "b.png", still_at=1.5)
