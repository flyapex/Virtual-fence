# Thesis proposal: Training Cattle in a Virtual Environment Before Real Virtual Fencing

## Purpose

Early virtual-fence training can concentrate electric-pulse exposure. This
thesis will test whether a carefully designed pre-training experience in a
simulated/immersive or mock environment improves subsequent responding to the
real collar's audio cue and reduces pulses at a new real boundary.

## Administrative constraints to complete

| Item | Current value |
| --- | --- |
| Degree | **UNSPECIFIED** (`MSc/PhD`) |
| Deadline | **UNSPECIFIED** |
| University format | **UNSPECIFIED** |
| Simulation type | **UNSPECIFIED** (`VR/projection`, `mock pen`, or `computational model`) |
| Collar system | **UNSPECIFIED** |
| Animal/site/ethics access | **UNSPECIFIED** |
| Hardware/budget | **UNSPECIFIED** |

These are decision inputs, not blanks to silently fill. They determine whether
the work is a computational planning thesis, a validated pre-training study, or
an animal experiment requiring formal approval.

## Research questions and hypotheses

1. Does simulation pre-training reduce real-collar pulse exposure in the first
   three days compared with conventional training?
   - H1: simulation-pre-trained groups have at least 30% fewer pulses per
     animal-day in that window.
2. Does pre-training improve audio-only responsiveness and learning speed?
   - H2: simulation-pre-trained groups have a higher audio-only success ratio
     and a shorter time-to-criterion.
3. Are apparent individual effects robust to social learning?
   - H3: treatment estimates remain directionally consistent when group
     clustering and recent group responses are accounted for.
4. Can a mock-boundary arm separate general context exposure from the proposed
   cue-transfer mechanism?
   - H4: mock-boundary outcomes differ from the simulation arm if the
     audio-to-pulse association, rather than context familiarity alone, matters.

## Outcomes

Primary outcome: group-level pulses per animal per day over real-training days
1–3. The preregistered planning threshold is a 30% reduction in simulation
pre-training versus conventional training.

Secondary outcomes: audio-only response ratio, time-to-criterion, escapes,
re-entry, response latency/distance where logs permit, and prespecified welfare
indicators. See [study design](study_design.md) for definitions.

## Design and analysis plan

Use three arms—conventional, simulation pre-training and mock-boundary pen—with
at least three independent groups per arm and 4–5 cattle per group. Randomise
groups, not individual cattle, and evaluate transfer at a new real test
location. The core model is a mixed count model with arm, day and their
interaction as fixed effects and group as a random effect, supported by
cluster-level/randomisation sensitivity analyses because group numbers are
small. Results will be reported as group-aware effect estimates and uncertainty.

The repository's agent-based model is a transparent design/power tool. It uses
Rescorla-Wagner audio-to-pulse learning, an assumed response function, and
assumed social facilitation. It supplies no biological parameter estimates and
cannot replace the transfer trial.

## Welfare measures

Use approval-specific pulse limits and stopping rules, pre- and post-session
health checks, behavioural observation, technical-failure logs, escape/re-entry
records and handler intervention records. Interpret fewer pulses alongside,
not instead of, containment and welfare indicators. Details are in
[ethics and preregistration](ethics_and_prereg.md).

## Limitations

- Cattle may not perceive a virtual or projected boundary/cue as intended.
- A simulated association may not transfer to a real GNSS collar context.
- Group social facilitation can mask or magnify an individual learning effect.
- Few groups limit precision and make random-effect estimates fragile.
- Candidate open data differ in environment, device, labels, animal population
  and study objectives; they are calibration-only.
- The collar system, simulation modality and operational constraints are still
  unspecified.

## Indicative 12-month timeline

| Months | Activity |
| --- | --- |
| 1–2 | Finalise constraints, supervisory protocol, systematic search and feasibility study. |
| 3 | Ethics/site/collar documentation and perceptual-validity pilot. |
| 4 | Freeze preregistration, randomisation, data dictionary and analysis code. |
| 5–6 | Implement/validate pre-training environment; staff training and dry run. |
| 7–8 | Run group-level trial with welfare monitoring and deviation log. |
| 9 | Clean and lock data; run preregistered analysis and robustness checks. |
| 10 | Interpret transfer, welfare and null findings with stakeholders. |
| 11 | Draft methods, results and discussion; reproduce figures/tables. |
| 12 | Revise, format to university requirements, archive code/protocol and submit. |

No date is assigned because the submission deadline is **UNSPECIFIED**.
