# Proposed three-arm transfer study

## Design question

Does pre-training cattle in a perceptually plausible simulated environment
reduce real-collar pulse exposure and speed audio-cue responding when the
animals later encounter a GNSS virtual fence?

This is a protocol concept, not approval to expose animals to cues or pulses.
The target collar system, animal/site access, simulation modality, budget,
degree requirements and university format remain **UNSPECIFIED / UNVERIFIED**.
They must be resolved with the supervisory team, veterinarian, welfare officer
and ethics committee before finalising this design.

## Units, arms and allocation

- Unit of randomisation and primary replication: a **group**, not an individual
  animal. Start with at least three independent groups per arm and 4–5 animals
  per group; the final number comes from a sensitivity analysis using credible
  pilot parameters.
- Arm 1, conventional: existing real-collar training at a real virtual boundary.
- Arm 2, simulation pre-training: planned audio/boundary pre-training in the
  selected VR, projection, mock-pen or computational modality, followed by the
  same real-collar training.
- Arm 3, mock-boundary pen: exposure to pen/boundary context without the
  hypothesised audio-to-pulse transfer element, then the same real-collar
  training.
- Randomise groups to arm before training using a recorded random sequence;
  stratify only on prospectively recorded factors (for example, site/paddock or
  prior collar exposure). Keep observers scoring outcomes blind to arm where
  feasible.
- Test transfer at a **new real test location**. The real boundary geometry,
  husbandry, group composition, collar settings and training schedule must be
  matched across arms as far as welfare and logistics allow.

## Prespecified primary outcome

For each group, calculate pulses per animal per day during the first three days
of real-collar training. The planning transfer criterion is at least **30% fewer
pulses** in the simulation arm than the conventional arm across that window.
The direction, window, formula, handling of zero exposure, and comparison must
be frozen in the preregistration before outcome data are examined.

## Secondary outcomes

- Audio-only success ratio: audio-only responses / all boundary interactions.
- Time-to-criterion: first of a preregistered run of days achieving a specified
  response rate. The planning default in the code is 80% for two consecutive
  days, and the reported value is the **first day of that run**, so the criterion
  is met on the reported day + 1. Both numbers are conventions to freeze in the
  preregistration, not measurements.
- Escapes/non-containment events, re-entry, latency to turn and distance to
  boundary, if device logs permit.
- Welfare indicators defined with the veterinarian before trial start (for
  example behavioural disturbance, injury checks, avoidance, health, and
  protocol deviations).

## Analysis

The primary descriptive and inferential summaries must preserve the group as
the experimental unit: show every group, group mean and uncertainty; do not
inflate sample size by treating within-group animals as independent replicates.

For count outcomes, fit a prespecified mixed model (negative-binomial or
Poisson only after checking dispersion) with arm, day and arm-by-day as fixed
effects, an offset for animal exposure, and group as a random effect. Include
animal nested within group only when the model is estimable; with the planned
small number of groups, report cluster-level sensitivity analyses/permutation
or randomisation-based comparisons as the more transparent primary check.

**Implementation status.** The planning code implements only the group-label
permutation contrast. It does **not** fit the mixed model above, so the power
numbers it reports are power for the permutation test, not for the primary
analysis described in this document. Any power claim taken from this repository
must say which of the two it refers to.

Report effect sizes and confidence intervals, not only p-values. Define missing
collar data, collar failures, animal withdrawal, escape handling, and any
exclusion rules before unblinding. Do not use the simulation's invented values
as empirical priors without independent justification.

