# Contributing

This repository supports a thesis planning study. Contributions are welcome,
but two rules come before style or speed.

1. **No number becomes a measurement by accident.** Every parameter in
   `SimulationParameters` and `PowerScenario` is an ASSUMPTION. A change that
   makes an assumed value look measured, or that removes a caution from output,
   a figure or a docstring, will be rejected.
2. **Reproducibility is a feature.** Identical inputs must produce identical
   outputs. Simulations use a local seeded generator; do not introduce global
   random state, wall-clock time or unordered iteration into a result path.

## Setting up

```powershell
git clone https://github.com/flyapex/Virtual-Fence.git
cd Virtual-Fence
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[plots,dev]"
.\.venv\Scripts\python.exe -m pytest
```

`.[dev]` adds the test runner, coverage, ruff and mypy. `.[plots]` adds
matplotlib, which only the figure and animation code needs.

## Before opening a pull request

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=vf_training --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
```

Optional but recommended: `pre-commit install` to run the same checks on commit.

## What a good change looks like

- **Model changes** state the behavioural assumption they encode, in the
  docstring, and add a test that pins the resulting behaviour. If a change makes
  an arm differ from `conventional`, say so in `CHANGELOG.md` and update
  `docs/study_design.md`.
- **New output** carries the caution that its numbers are simulated assumptions,
  and never prints or draws a value without the assumption that produced it.
- **New options** appear in `--help`, in `README.md`, and in `CHANGELOG.md`.
- **Statistical changes** explain the estimand, not just the implementation. The
  analysis unit is the group; keep it that way unless the design changes.
- **Figures** are generated, not committed by hand. If a plotted quantity
  changes, regenerate `docs/figures/` with:

  ```powershell
  vf-simulate --arm simulation --tau 0.60 --plot --compare-arms --outdir docs/figures
  vf-power --replications 500 --plot --outdir docs/figures
  vf-play --gif --outdir docs/figures
  vf-play --still --outdir docs/figures

  # the committed names are the ones the README embeds
  Move-Item docs/figures/days_arms_tau0.60_seed20261010.png      docs/figures/arms_day_by_day.png
  Move-Item docs/figures/power_grid_rep500_seed20261010.png      docs/figures/power_grid.png
  Move-Item docs/figures/playback_simulation_tau0.60_seed20261010.gif docs/figures/playback.gif
  Move-Item docs/figures/playback_simulation_tau0.60_seed20261010_still.png docs/figures/playback_still.png
  ```

## Reporting problems

Open an issue at https://github.com/flyapex/Virtual-Fence/issues. For anything
about the model's behaviour, include the exact command, the seed, and the
printed output, so the run can be reproduced.
