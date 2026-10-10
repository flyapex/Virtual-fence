# vf-sim-training

Planning code for the thesis **"Training Cattle in a Virtual Environment Before
Real Virtual Fencing"**. It is an intentionally simple, reproducible
agent-based model of cattle encountering a virtual-fence boundary.

The simulation asks a planning question: under explicit, unmeasured assumptions,
would transfer from a pre-training environment reduce pulse exposure during the
first three days of real virtual-fence training? It **does not establish animal
learning, welfare, or transfer effectiveness**.

## What is included

- Rescorla-Wagner learning of the audio-to-pulse association.
- Audio-only response probability that increases with associative strength.
- A group social-facilitation term based on recent responders.
- Three study arms: `conventional`, `simulation`, and `mock_boundary`.
- Group-level Monte Carlo power calculations, including the preregistered
  planning target of a 30% lower pulse rate over the first three days.
- Generic, schema-inspecting local data loaders. They report actual files and
  headers; they never assume source column names.

Every numeric model parameter is an **ASSUMPTION**, not a measurement. Candidate
datasets are for model calibration and workflow development only; none can
substitute for the proposed transfer experiment.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
pytest
python scripts/run_simulation.py --arm simulation --tau 0.60 --seed 20261010
python scripts/run_power_analysis.py --replications 500 --seed 20261010
```

Use `--help` with either script for options. Results printed by these scripts
are simulated outputs conditional on their assumptions, not experimental
findings.

## Project layout

```text
src/vf_training/       simulation, metrics, power, and cautious data inspection
scripts/               command-line entry points
tests/                 deterministic unit tests
docs/                  proposal, design, ethics, sources, search protocol
data/raw/              locally obtained data only (ignored by Git)
data/processed/        derived local data only (ignored by Git)
results/               local generated outputs (ignored by Git)
```

See [the proposal](docs/thesis_proposal.md), [study design](docs/study_design.md),
[dataset verification](docs/datasets.md), and
[ethics and preregistration](docs/ethics_and_prereg.md) before treating this as
a study protocol.

