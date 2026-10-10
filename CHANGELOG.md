# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every release is planning software: no release contains measured animal data,
and no release changes the fact that all model parameters are assumptions.

## [Unreleased]

### Added

- `vf-calibrate` / `scripts/run_calibration.py`: fits the behavioural parameters
  to real animal-day audio and pulse records. A USDA-schema loader that reports
  the columns it matched and refuses to guess, encounter and escape rates taken
  from the data instead of fitted, a grid fit over four parameters, marginal
  identifiability profiles, and `--self-test` to verify the pipeline on
  model-generated pseudo-data without any download.
- `vf-sensitivity` / `scripts/run_sensitivity_analysis.py`: Morris screening of
  the seven assumed behavioural parameters against the planned pulse reduction,
  with `mu`, `mu_star` and `sigma` per assumption, a two-panel figure, and an
  injectable target so the screening itself is tested without the model. At the
  defaults, `tau` dominates the answer (`mu_star` 0.431 versus 0.155 or less).
- `docs/publication_readiness.md`: an honest audit of what this repository can
  and cannot support for a journal submission, with a gap register and four
  routes (calibrated design analysis, empirical trial, software paper, submit
  as-is).

## [0.2.0] - 2026-10-10

### Added

- Figure output for simulation and power runs: `--plot`, `--compare-arms`,
  `--outdir`, `--format` (`png`, `svg`, `pdf`) and `--dpi`.
- `--show` to hold a figure open in an interactive window, with a named window
  so it is identifiable in the taskbar.
- Animated playback of one group meeting the boundary, `vf-play` /
  `scripts/show_simulation.py`, with window, GIF and still-frame output.
- `vf-play --live`: one field panel with live controls (arm, animals, days, tau,
  learning rate, speed, strength bars, replay, pause, new seed, reset) that
  re-simulate as you change them, plus `--strength` to start with the bars shown.
  A headless machine gets a clear message instead of a silent no-op.
- Per-day aggregation (`daily_summary`, `DaySummary`) in `metrics`, whose
  pulse rate uses the same animal-day denominator as the power module.
- Console entry points: `vf-simulate`, `vf-power`, `vf-play`, `vf-inspect`.
- `py.typed` marker, so type checkers use the shipped annotations.
- Rejection rate reported alongside successful-trial power, so the test's size is
  visible on its own (at `tau = 0` the reduction rule suppresses successes but
  not rejections).
- `minimum_attainable_p`, plus a per-row `note` column that separates the two
  reasons a row reads zero: a design floor at or above alpha, and a simulated
  reduction below the target.
- `--groups-per-arm` and `--taus` on `vf-power`, so the grid is not fixed.
- Continuous integration now runs lint, format check, type check, tests on a
  Python 3.10-3.13 matrix with an 85% coverage gate, and a packaging build job
  that installs the wheel and runs the installed console commands.

### Changed

- `matplotlib` is an optional `plots` extra; text output never requires it.
- `inspect_dataset` and `read_csv_rows` return structured results instead of
  printing, and `vf-inspect` prints them for humans. A missing path now raises
  `FileNotFoundError` rather than reporting an empty result.
- `PowerScenario` requires at least three groups per arm, matching the study
  design, instead of allowing a design that cannot reject.
- Figure and animation tests are skipped, not failed, when the extra is absent.

### Fixed

- The dataset licence conflict was attached to the wrong record: the dairy
  record is CC BY 4.0 and the Japanese Black record is the one that is
  UNVERIFIED FOR REUSE, matching `docs/datasets.md`.
- The conventional and mock-boundary arms are reported as numerically identical
  series on any figure that overlays them, rather than drawing one line twice,
  and the power table and figure label that arm as a null by construction.
- Docstrings that contradicted behaviour: power reported as a rejection
  probability when it also requires the reduction rule, an interaction described
  as meeting a real boundary, the shuffle frequency, the daily versus pooled
  pulse window, and the first-day-of-run convention in `time_to_criterion`.
- A figure written with `--show` now reports its path before the window opens,
  so a blocking window is never mistaken for a hung command.

## [0.1.0] - 2026-10-10

### Added

- Rescorla-Wagner learning of the audio-to-pulse association with a
  social-facilitation term, three study arms (`conventional`, `simulation`,
  `mock_boundary`), and seeded, reproducible group simulations.
- Group-level Monte Carlo power calculations with an exact or Monte Carlo
  group-label permutation test and the 30% pulse-reduction requirement.
- Schema-inspecting local data loaders that never assume source column names.
- Documentation set: proposal, study design, ethics and preregistration,
  dataset verification, literature search protocol and chapter outline.

[Unreleased]: https://github.com/flyapex/Virtual-Fence/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/flyapex/Virtual-Fence/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/flyapex/Virtual-Fence/releases/tag/v0.1.0
