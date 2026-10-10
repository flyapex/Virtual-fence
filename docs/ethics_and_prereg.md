# Ethics and preregistration guardrails

## Welfare principle

The study's motivation is to reduce aversive real-collar exposure, not to add
unnecessary exposure. The simulation code does not authorise real-world use of
audio cues, electric pulses, collars or immersive hardware. No animal work may
start without applicable ethics approval, veterinary sign-off, trained staff,
site permission and a collar system-specific welfare protocol. All of these are
currently **UNVERIFIED / UNSPECIFIED**.

## Before any animal enrolment

- Obtain protocol approval from the relevant animal ethics body and document the
  exact collar system, cue parameters, pulse limits, clinician/veterinarian
  oversight and adverse-event reporting route.
- Demonstrate that the selected virtual/projection/mock setting is safe and
  perceptually usable for cattle before claiming it is a pre-training
  environment. Check habituation, visual angle, audio level/direction,
  distraction, social separation and escape routes.
- Define stopping/withdrawal criteria with the veterinarian and ethics body,
  including distress, injury, abnormal behaviour, repeated non-containment,
  technical faults, and any pulse-exposure ceiling. No numeric ceiling is
  specified here because it would be a welfare decision requiring local
  approval.
- Train handlers in low-stress stockmanship and device failure response. Record
  all interventions, including collar removal and deviations.

## Preregister before data collection

Freeze the following in a timestamped protocol/repository release:

1. Groups, eligibility, randomisation/stratification and target sample size.
2. Full arm procedures, test-location definition, collar configuration and
   simulation modality.
3. Primary endpoint: group-level pulses per animal per day in real-training days
   1–3; superiority criterion: at least 30% lower rate for simulation versus
   conventional.
4. Secondary endpoints, time-to-criterion rule, denominator for interactions,
   escape definition, model formula and sensitivity analyses.
5. Data-quality rules, missingness, blinded outcome handling, exclusions and
   adverse-event/stopping rules.
6. Dataset provenance. Candidate public datasets are calibration-only and will
   not be presented as causal evidence for transfer.

## Safeguards against overclaiming

- Treat `tau` in the model as an **ASSUMPTION** about transfer, not a measured
  treatment effect.
- The proposed design can distinguish pre-training arms only if social learning
  and group clustering are modelled and replicated at group level.
- A reduction in pulses alone is insufficient to claim improved welfare; report
  containment, avoidance, health and behavioural measures together.
- Calibrate only after checking source licences and record versions. The
  Japanese Black dataset licence conflict is unresolved and must not be reused
  unless clarified.
