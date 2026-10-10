# Publication readiness: what this repository can and cannot support

**Audited 2026-10-10** against the repository state at commit `b608e99` (tag
`v0.2.0` plus the live playback). This document is an honest gap analysis, not a
plan of record. It separates *software* readiness, which is largely done, from
*scientific* readiness, which is largely not.

Read it before promising a submission to anyone, including yourself.

## 1. What exists today, verified

| Area | Status | Evidence |
| --- | --- | --- |
| Simulation model | Implemented | Rescorla-Wagner learning, social facilitation, three arms, seeded and reproducible (`src/vf_training/model.py`) |
| Outcome definitions | Implemented | Group pulse rate over days 1-3, audio-only success ratio, time-to-criterion, escapes (`metrics.py`) |
| Power calculation | Implemented, **for the permutation contrast only** | `power.py`; the protocol's mixed count model is not implemented |
| Figures and playback | Implemented | Day-by-day, power grid, GIF/still, live adjustable window |
| Software engineering | Publication-grade | 63 tests, 87% branch coverage, ruff + mypy clean, CI on Python 3.10-3.13, wheel build job, MIT licence, `py.typed` |
| Documentation | Proposal, design, ethics, datasets, search protocol, chapter outline, CHANGELOG, CONTRIBUTING, CITATION.cff | `docs/` |
| Citation artefacts | Partial | Tags `v0.1.0`, `v0.2.0` exist; **no DOI**, author name in `CITATION.cff` is still the GitHub handle |
| Data | **None** | `data/raw/` and `data/processed/` hold only `.gitkeep` |
| Calibration to data | **None** | No code consumes measured data; the model supplies no biological parameter estimates |
| Sensitivity analysis | **None** | Promised in four design documents; `vf-power` varies only groups per arm and `tau` |
| Literature review | **Not started** | All seven searches in `docs/search_log.md` show `Executed? No`; `references.bib` has 10 entries, 6 flagged TODO/unverified |
| Preregistration | **Not done** | The 30% target, days 1-3 window and time-to-criterion default are planning conventions, not registered |
| Study protocol inputs | **Unspecified** | Degree, deadline, simulation type, collar system, site/ethics access and budget are all `UNSPECIFIED` in `docs/thesis_proposal.md` |

## 2. The honest verdict on a Q1 submission today

Submitting the current artefact as a research paper would very likely be
desk-rejected or heavily criticised, and the reasons are specific rather than
stylistic:

1. **No data, no calibration.** Every behavioural parameter is declared an
   assumption. A modelling paper with no empirical anchor is not a Q1 result;
   reviewers will ask what the model is calibrated or validated against.
2. **The headline number answers the wrong question.** Power is computed for a
   group-label permutation test, while the protocol's primary analysis is a mixed
   count model with a group random effect. Reviewers who read both will find the
   mismatch.
3. **The mock-boundary arm is a null by construction.** It shares the
   conventional mechanism, so hypothesis H4 cannot be evaluated. As written, the
   third arm adds nothing.
4. **No sensitivity analysis**, so no claim about robustness can survive review.
5. **No literature review**, so the contribution and gap are unestablished.
6. **Design floor**: at three groups per arm no effect of any size can reject, and
   a Q1 reviewer will spot structural zeros in a power table immediately.

Points 1, 4 and 5 are the real blockers; 2, 3 and 6 are defects this repository
has already documented and can fix.

## 3. Four routes, in descending order of Q1 plausibility

Verify each journal's current aims, scope and quartile at submission time; these
change annually and are not asserted here.

### Route A: design-analysis paper (a simulation study), no animals

**Claim:** "How many groups does a virtual-fence pre-training trial need, and how
does that answer depend on the behavioural assumptions nobody has measured?"

**Requires:** calibration against at least one real virtual-fence dataset;
a global sensitivity analysis; the mixed-model power implemented; ADEMP reporting;
ODD description of the model.

**Realistic venues:** applied modelling or precision-livestock outlets (for
example *Computers and Electronics in Agriculture*, *Animal*, *Ecological
Modelling*, *Simulation Modelling Practice and Theory*). This is the most
attainable Q1 route without animal work, and it strengthens the thesis either way.

### Route B: the empirical trial paper

**Claim:** pre-training in a simulated environment reduces pulse exposure in days
1-3 of real training.

**Requires:** ethics approval, animals, site, collars, budget, staff, and the
preregistration — none of which the repository can supply. Strongest Q1 ceiling;
the simulation then becomes the design and power appendix.

### Route C: software paper (achievable soonest)

**Claim:** an open, reproducible tool for planning virtual-fence pre-training
trials.

**Requires:** a statement of need, documentation, tests, an OSI licence and a
Zenodo DOI — the repository already satisfies most of it (see
[JOSS submission requirements](https://joss.theoj.org/about)). A DOI plus a
software paper makes the tool citable and gives a real publication while Route A
or B matures.

### Route D: submit as-is

Not recommended. It forfeits the good faith the repository has earned.

## 4. Gap register

Severity: **B** = blocks any Q1 submission, **M** = major revision risk,
**m** = minor.

| # | Gap | Sev | Owner | Effort | Notes |
| --- | --- | --- | --- | --- | --- |
| G1 | No measured data in `data/raw` | B | you | Download, minutes | The USDA record (CC0 1.0, DOI 10.15482/USDA.ADC/30888611) contains per-animal `No. Audios` and `No. Pulses`, which is exactly the outcome structure this model needs |
| G2 | ~~No calibration code~~ **CLOSED 2026-10-10** | — | done | `vf-calibrate`: USDA-schema loader, grid fit with measured encounter and escape rates, marginal identifiability profiles, and a self-test that recovers model-generated pseudo-data before real data are needed. Waiting on G1 to run for real |
| G3 | ~~No sensitivity analysis~~ **CLOSED 2026-10-10** | — | done | `vf-sensitivity`: Morris screening over seven assumptions, 2 s at defaults. Result: transfer (`tau`) dominates at `mu_star` 0.431 versus 0.155 or less for everything else. Global variance decomposition and design-parameter screening remain open |
| G4 | Literature review not executed | B | you (+me to seed) | Week | Seven frozen strings exist; run them, screen, record counts, verify the 6 unverified bib entries |
| G5 | Power for the wrong test | M | me | Days | Implement group-random-effect count-model power (simulate, fit, reject) alongside the permutation contrast |
| G6 | Mock arm is a null | M | you decide, me implement | Hours | Give it a distinct mechanism (context exposure without the audio-pulse contingency) or drop it and revise H4 |
| G7 | No ADEMP statement | M | me | Hours | Purpose, data-generating mechanism, estimands, methods, performance measures — see [Morris et al. 2019](https://onlinelibrary.wiley.com/doi/full/10.1002%2Fsim.8086) |
| G8 | No ODD model description | M | me | Hours | Standard ABM description — see the [ODD protocol](https://pubs.usgs.gov/publication/70161470) |
| G9 | Social window saturates | M | you decide | Hours | Measured 1.0 social fraction for most of a run; either shorten the window or report it as a limitation with evidence |
| G10 | No DOI / frozen release | M | me | Minutes | Mint a Zenodo DOI from tag `v0.2.0`; the repository already prints rollback-grade provenance |
| G11 | Author identity is a placeholder | M | you | Minutes | `CITATION.cff` needs the real name and, if held, an ORCID |
| G12 | Preregistration not filed | M (Route B), m (A) | you | Hours | OSF registration freezing the 30% target, window, criterion and analysis |
| G13 | No environment lock | m | me | Hours | Pinned lockfile or container so figures rebuild byte-identically years from now |
| G14 | Protocol inputs unspecified | B for Route B | you | — | Degree, deadline, simulation type, collar, site, ethics, budget |

## 5. Recommended scope

**If the target is a Q1 paper within one semester:** Route A, executed as

1. G1 + G2 — bring in the CC0 dataset and calibrate. Without this, stop; nothing
   else rescues the paper.
2. G3 — sensitivity analysis, with a tornado and a rank-correlation figure.
3. G5 — mixed-model power beside the permutation contrast, so the number matches
   the protocol.
4. G7 + G8 — ADEMP and ODD sections, written as repository documents first.
5. G6 + G9 — decide the mock mechanism and the social window, and say why.
6. G4 — the review, run for real, with the PRISMA counts.
7. G10 + G11 — DOI and author identity, then a Route C software note if time
   allows.

**What this buys:** a calibrated, sensitivity-tested design analysis with a
citable tool behind it. That is a defensible Q1 modelling paper, and it is also
the methods chapter of the thesis regardless of whether the trial ever runs.

**What it does not buy:** any claim about real cattle. Every output stays labelled
as a simulated planning estimate, which is exactly what keeps the paper honest.

## 6. Acceptance criteria for "Q1-ready"

- A calibrated model whose parameters trace to a named dataset and version.
- A sensitivity analysis whose conclusions do not flip across plausible
  assumptions, or an explicit statement of where they do.
- Power reported for the analysis the protocol actually specifies.
- ADEMP and ODD statements, a data/code availability statement, and a DOI.
- Every figure regenerable from a tagged release in one command.
- No remaining claim in any document that the code does not support.
