"""Tests for calibration against animal-day boundary records."""

from pathlib import Path

import pytest

from vf_training.calibration import (
    AnimalDayObservation,
    CalibrationGrid,
    ObservedProfile,
    distance,
    fit_parameters,
    format_calibration,
    load_observations,
    observations_from_rows,
    profile_from_observations,
    pseudo_data,
    simulated_profile,
)
from vf_training.model import SimulationParameters


def test_observations_are_summed_per_animal_day() -> None:
    rows = [
        {"Neckband ID": "A1", "Day": "1", "No. Audios": "3", "No. Pulses": "1"},
        {"Neckband ID": "A1", "Day": "1", "No. Audios": "2", "No. Pulses": "0"},
        {"Neckband ID": "A2", "Day": "1", "No. Audios": "1", "No. Pulses": "4"},
        {"Neckband ID": "A1", "Day": "2", "No. Audios": "5", "No. Pulses": "0"},
    ]

    observations, matched = observations_from_rows(rows)

    assert matched == {
        "audio": "No. Audios",
        "pulse": "No. Pulses",
        "day": "Day",
        "animal": "Neckband ID",
    }
    by_key = {(item.animal, item.day): item for item in observations}
    assert by_key[("A1", 1)].audios == 5
    assert by_key[("A1", 1)].pulses == 1
    assert by_key[("A1", 1)].interactions == 6
    assert by_key[("A2", 1)].audio_only_ratio == pytest.approx(0.2)
    assert by_key[("A1", 2)].audio_only_ratio == pytest.approx(1.0)


def test_timestamps_are_numbered_from_the_earliest_date() -> None:
    rows = [
        {
            "Animal_ID": "A",
            "Time (UTC)": "2025-04-19 08:00:00",
            "No. Audios": "2",
            "No. Pulses": "0",
        },
        {
            "Animal_ID": "A",
            "Time (UTC)": "2025-04-17 09:00:00",
            "No. Audios": "0",
            "No. Pulses": "3",
        },
        {
            "Animal_ID": "A",
            "Time (UTC)": "2025-04-18 09:00:00",
            "No. Audios": "1",
            "No. Pulses": "1",
        },
    ]

    observations, _matched = observations_from_rows(rows)

    assert {item.day for item in observations} == {1, 2, 3}
    assert [item.pulses for item in sorted(observations, key=lambda item: item.day)] == [3, 1, 0]


def test_a_missing_column_is_refused_rather_than_guessed() -> None:
    rows = [{"Animal_ID": "A", "Day": "1", "No. Audios": "2"}]

    with pytest.raises(ValueError, match="Could not find columns"):
        observations_from_rows(rows)


def test_an_unusable_day_field_is_refused() -> None:
    rows = [{"Animal_ID": "A", "Day": "whenever", "No. Audios": "2", "No. Pulses": "1"}]

    with pytest.raises(ValueError, match="neither a number nor an ISO date"):
        observations_from_rows(rows)


def test_loader_skips_files_without_the_needed_columns(tmp_path: Path) -> None:
    (tmp_path / "Groups.csv").write_text("Animal_ID,Group,TRT\nA1,1,control\n", encoding="utf-8")
    (tmp_path / "collar.csv").write_text(
        "Neckband ID,Day,No. Audios,No. Pulses\nA1,1,6,2\nA1,2,8,0\n", encoding="utf-8"
    )

    observations, matched, source = load_observations(tmp_path)

    assert source.name == "collar.csv"
    assert matched["audio"] == "No. Audios"
    assert len(observations) == 2


def test_loader_reports_every_rejected_file(tmp_path: Path) -> None:
    (tmp_path / "Groups.csv").write_text("Animal_ID,Group\nA1,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No CSV carried the required"):
        load_observations(tmp_path)


def test_profile_measures_encounter_and_escape_rates_directly() -> None:
    observations = (
        AnimalDayObservation("A", 1, audios=6, pulses=2),
        AnimalDayObservation("A", 2, audios=8, pulses=0),
        AnimalDayObservation("B", 1, audios=4, pulses=4, escapes=1),
        AnimalDayObservation("B", 2, audios=7, pulses=1),
    )

    profile = profile_from_observations(observations)

    assert profile.animals == 2
    assert profile.days == 2
    assert profile.animal_days == 4
    assert profile.interactions_per_animal_day == pytest.approx((8 + 8 + 8 + 8) / 4)
    assert profile.escape_rate == pytest.approx(1 / 7)
    assert profile.pulses_per_animal_day == pytest.approx((3.0, 0.5))
    assert profile.audio_only_ratio[0] == pytest.approx((0.75 + 0.5) / 2)


def test_distance_is_zero_for_identical_profiles_and_grows_with_error() -> None:
    profile = ObservedProfile(
        animals=3,
        days=2,
        animal_days=6,
        interactions_per_animal_day=8.0,
        escape_rate=0.0,
        pulses_per_animal_day=(3.0, 1.0),
        audio_only_ratio=(0.7, 0.9),
    )
    shifted = ObservedProfile(
        animals=3,
        days=2,
        animal_days=6,
        interactions_per_animal_day=8.0,
        escape_rate=0.0,
        pulses_per_animal_day=(4.0, 1.5),
        audio_only_ratio=(0.6, 0.8),
    )

    assert distance(profile, profile) == pytest.approx(0.0)
    assert distance(profile, shifted) > 0.0
    with pytest.raises(ValueError, match="same number of days"):
        distance(profile, ObservedProfile(3, 1, 3, 8.0, 0.0, (1.0,), (0.5,)))


def test_grid_drops_parameter_sets_that_are_not_valid_models() -> None:
    grid = CalibrationGrid(
        learning_rate=(0.2,),
        baseline_response_probability=(0.10,),
        associative_response_weight=(0.70,),
        social_response_weight=(0.20,),
    )

    points = grid.points()

    assert len(points) == 1
    total = (
        points[0].baseline_response_probability
        + points[0].associative_response_weight
        + points[0].social_response_weight
    )
    assert total <= 1.0


def test_self_test_recovers_the_generating_profile(tmp_path: Path) -> None:
    """The pipeline must recover model-generated data before it meets real data."""
    truth = SimulationParameters(
        learning_rate=0.25,
        baseline_response_probability=0.05,
        associative_response_weight=0.65,
        social_response_weight=0.10,
    )
    observed = pseudo_data(truth, animals=4, days=4, seed=7)
    coarse = CalibrationGrid(
        learning_rate=(0.15, 0.25, 0.35),
        baseline_response_probability=(0.00, 0.05),
        associative_response_weight=(0.55, 0.65),
        social_response_weight=(0.05, 0.15),
        seeds=(7,),
    )

    fit = fit_parameters(observed, coarse)
    recovered = fit.simulate_profile(seed=7)
    wrong = simulated_profile(
        SimulationParameters(learning_rate=0.05, associative_response_weight=0.30), observed, seed=7
    )

    assert fit.distance < distance(observed, wrong)
    assert distance(observed, recovered) < 0.05
    assert fit.grid_size == len(coarse.points())
    assert {profile.parameter for profile in fit.profiles} == {
        "learning_rate",
        "baseline_response_probability",
        "associative_response_weight",
        "social_response_weight",
    }


def test_report_states_what_is_measured_and_what_is_fitted() -> None:
    truth = SimulationParameters(learning_rate=0.25, associative_response_weight=0.65)
    observed = pseudo_data(truth, animals=3, days=3, seed=3)
    fit = fit_parameters(
        observed,
        CalibrationGrid(
            learning_rate=(0.20, 0.30),
            baseline_response_probability=(0.05,),
            associative_response_weight=(0.60,),
            social_response_weight=(0.10,),
            seeds=(3,),
        ),
    )

    report = format_calibration(fit)

    assert "not measurements" in report
    assert "measured, not fitted" in report
    assert "identifiability" in report
    for name in ("learning_rate", "social_response_weight"):
        assert name in report
