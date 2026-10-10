"""Agent-based virtual-fence learning model.

This module is a planning model, not a validated representation of cattle.
Every value in :class:`SimulationParameters` is an explicit ASSUMPTION.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
from typing import Literal

Arm = Literal["conventional", "simulation", "mock_boundary"]


@dataclass(frozen=True)
class SimulationParameters:
    """Unmeasured planning assumptions for one simulated group.

    ASSUMPTION: `learning_rate` is the Rescorla-Wagner alpha parameter and the
    pulse outcome has magnitude one. ASSUMPTION: an animal meets the boundary
    `interactions_per_animal_per_day` times each day. ASSUMPTION: a successful
    response to audio alone avoids a pulse. ASSUMPTION: a non-response receives
    a pulse and may escape with `escape_probability_after_nonresponse`.

    The simulated and mock environments never deliver real electric pulses in
    this model. `simulated_pretraining_trials` represents an unmeasured virtual
    learning opportunity, and `tau` determines how much of that learned state
    transfers to the real collar context. The mock-boundary arm has no
    audio-to-pulse association transferred by design.
    """

    n_animals: int = 5
    days: int = 7
    interactions_per_animal_per_day: int = 8
    learning_rate: float = 0.25
    baseline_response_probability: float = 0.05
    associative_response_weight: float = 0.70
    social_response_weight: float = 0.20
    social_memory_interactions: int = 10
    escape_probability_after_nonresponse: float = 0.04
    simulated_pretraining_trials: int = 12

    def validate(self) -> None:
        """Raise a clear error for parameter values outside probability bounds."""
        if self.n_animals < 1 or self.days < 1 or self.interactions_per_animal_per_day < 1:
            raise ValueError("Counts must be at least one.")
        if self.social_memory_interactions < 1 or self.simulated_pretraining_trials < 0:
            raise ValueError("Memory must be positive and pre-training trials non-negative.")
        probabilities = {
            "learning_rate": self.learning_rate,
            "baseline_response_probability": self.baseline_response_probability,
            "associative_response_weight": self.associative_response_weight,
            "social_response_weight": self.social_response_weight,
            "escape_probability_after_nonresponse": self.escape_probability_after_nonresponse,
        }
        for name, value in probabilities.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1.")
        if (
            self.baseline_response_probability
            + self.associative_response_weight
            + self.social_response_weight
            > 1.0
        ):
            raise ValueError("Response components must sum to no more than one.")


@dataclass(frozen=True)
class Interaction:
    """One encounter with the real virtual-fence boundary."""

    group_id: str
    arm: Arm
    day: int
    interaction_number: int
    animal_id: int
    associative_strength_before: float
    associative_strength_after: float
    social_response_fraction: float
    response_probability: float
    audio_only_response: bool
    pulse_delivered: bool
    escaped: bool


@dataclass(frozen=True)
class SimulationResult:
    """Complete event history for one independently simulated group."""

    group_id: str
    arm: Arm
    tau: float
    events: tuple[Interaction, ...]
    final_associative_strengths: tuple[float, ...]


def pretraining_strength(parameters: SimulationParameters) -> float:
    """Return the expected virtual associative strength after pre-training.

    This is the closed-form result of repeated Rescorla-Wagner updates towards a
    unit outcome. It is a modelling convenience, not observed animal learning.
    """
    return 1.0 - (1.0 - parameters.learning_rate) ** parameters.simulated_pretraining_trials


def initial_associative_strength(
    arm: Arm, tau: float, parameters: SimulationParameters
) -> float:
    """Set real-context association at the start of training for an arm."""
    if not 0.0 <= tau <= 1.0:
        raise ValueError("tau must be between 0 and 1.")
    if arm == "simulation":
        return tau * pretraining_strength(parameters)
    if arm in {"conventional", "mock_boundary"}:
        return 0.0
    raise ValueError(f"Unknown arm: {arm}")


def _recent_response_fraction(history: deque[set[int]], n_animals: int) -> float:
    """Fraction of unique group members responding in the recent event window."""
    recent_responders: set[int] = set()
    for responders in history:
        recent_responders.update(responders)
    return len(recent_responders) / n_animals


def _response_probability(
    strength: float, social_fraction: float, parameters: SimulationParameters
) -> float:
    """Combine assumed baseline, associative, and social response components."""
    probability = (
        parameters.baseline_response_probability
        + parameters.associative_response_weight * strength
        + parameters.social_response_weight * social_fraction
    )
    return max(0.0, min(1.0, probability))


def simulate_group(
    arm: Arm,
    *,
    tau: float = 0.0,
    parameters: SimulationParameters | None = None,
    group_id: str = "group-1",
    seed: int = 20261010,
) -> SimulationResult:
    """Simulate a single group under one arm with a fixed pseudo-random seed.

    The animal order is shuffled each day, but all stochastic decisions use the
    local seeded generator, so identical inputs reproduce identical histories.
    """
    parameters = parameters or SimulationParameters()
    parameters.validate()
    if arm != "simulation" and tau != 0.0:
        raise ValueError("tau is only meaningful for the simulation arm.")

    rng = random.Random(seed)
    strengths = [initial_associative_strength(arm, tau, parameters)] * parameters.n_animals
    history: deque[set[int]] = deque(maxlen=parameters.social_memory_interactions)
    events: list[Interaction] = []
    interaction_number = 0

    for day in range(1, parameters.days + 1):
        animal_order = list(range(parameters.n_animals))
        for _ in range(parameters.interactions_per_animal_per_day):
            rng.shuffle(animal_order)
            for animal_id in animal_order:
                interaction_number += 1
                strength_before = strengths[animal_id]
                social_fraction = _recent_response_fraction(history, parameters.n_animals)
                probability = _response_probability(strength_before, social_fraction, parameters)
                audio_only_response = rng.random() < probability
                pulse_delivered = not audio_only_response
                escaped = pulse_delivered and (
                    rng.random() < parameters.escape_probability_after_nonresponse
                )
                if pulse_delivered:
                    strengths[animal_id] += parameters.learning_rate * (1.0 - strengths[animal_id])
                history.append({animal_id} if audio_only_response else set())
                events.append(
                    Interaction(
                        group_id=group_id,
                        arm=arm,
                        day=day,
                        interaction_number=interaction_number,
                        animal_id=animal_id,
                        associative_strength_before=strength_before,
                        associative_strength_after=strengths[animal_id],
                        social_response_fraction=social_fraction,
                        response_probability=probability,
                        audio_only_response=audio_only_response,
                        pulse_delivered=pulse_delivered,
                        escaped=escaped,
                    )
                )
    return SimulationResult(
        group_id=group_id,
        arm=arm,
        tau=tau,
        events=tuple(events),
        final_associative_strengths=tuple(strengths),
    )

