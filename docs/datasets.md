# Candidate datasets: verification and permitted role

**Checked 2026-10-10.** These sources are for **model calibration and workflow
development only**. They cannot answer the causal transfer question, replace
the proposed trial, or be pooled as though they were arms of that trial.

The source links below were resolved from their record metadata or DOI landing
page. The listed sizes are the sum of files in the checked record version, not
the size of a future download. Column lists come from a direct header read where
stated. The loaders in `src/vf_training/data_loaders.py` inspect local headers
again rather than relying on this document.

| Candidate | Link and checked licence | Checked record contents | Verified variables / status | Calibration-only use |
| --- | --- | --- | --- | --- |
| GNSS tracking, 39 adult Limousine cows | [Zenodo 17338610](https://zenodo.org/records/17338610), CC BY 4.0, open | 10 files; 2,193,477 bytes (2.09 MiB): `data.csv`, `cow_collar.csv`, farm perimeter shapefile components, README, Quarto and HTML | `data.csv`: first unnamed field, `id_collar`, `lng`, `lat`, `time_stamp`; `cow_collar.csv`: `idcollar`, `eartag`, `birth`, `age`, `type`, `breed`. Source description states 39 cows. | Boundary-approach and movement-rate assumptions; no audio, pulse, or transfer outcome. |
| Virtual-fence experimental data, 27 cattle | [DOI 10.15482/USDA.ADC/30888611](https://doi.org/10.15482/USDA.ADC/30888611), CC0 1.0 | 14 files; 6,036,302 bytes (5.76 MiB): KML boundaries, R script, five CSVs, README and data dictionary | Direct headers: collar files: `Time (UTC)`, `Neckband ID`, latitude/longitude, `No. Audios`, `No. Pulses`; `Escapes.csv`: `Animal_ID`, `Group`, `Period`, `Escape_Type`, `Escape_no`, `Day`, `Time`, `TRT`; `Extinction.csv`: `Animal_ID`, `Group`, `Day`, `Time`, `TRT`, blank field, prose-note field; `Groups.csv`: `Animal_ID`, `Neckband ID`, `Group`, `N`, `TRT`, `Weight_4/17/2025_lb`. The group file contains 27 distinct `Animal_ID` values. | Plausible calibration/sensitivity source for encounter, audio, pulse and escape processes. It is not a pre-training transfer trial. |
| Beef behaviour sensors | [Figshare 28801181](https://figshare.com/articles/dataset/28801181), CC BY 4.0 | 4 files; 474,992 bytes (0.45 MiB): two CSVs and two READMEs | Direct headers: `Cattle_behavior_data.csv`: `Breed`, `ID`, `MI`, `State`, `Behavior`; `cattle_behavior_data_time_V2.csv`: `Breed`, `ID`, `Time.MTD`, `MI`, `State`, `Behavior`. The first file contains 24 distinct `ID` values. | Behaviour-state and activity assumptions only; no virtual-fence events. |
| Dairy activity and barn location | [Zenodo 14886594](https://zenodo.org/records/14886594), CC BY 4.0, open | 3 CSVs; 79,918,291 bytes (76.22 MiB) | Direct headers: activity: `timestamp`, `cow_name`, `mi`, `steps`; both location files: `timestamp`, `cow_name`, `area`. Source description says 20 cows, 1-minute sampling and 55 days. | Activity/location aggregation and loader testing; indoor barn data do not validate pasture-fence transfer. |
| Japanese Black cow behaviour | [Zenodo 5849025](https://zenodo.org/records/5849025) | One ZIP; 14,460,415 bytes (13.79 MiB), described as six cow CSVs | Record-declared fields: `TimeStamp_UNIX`, `TimeStamp_JST`, `AccX`, `AccY`, `AccZ`, `Label`; the record describes six cows, 25 Hz data and 13 labelled behaviours. **UNVERIFIED by direct file read:** download endpoint returned HTTP 403 in this review. | Accelerometer/behaviour-state calibration only; no virtual-fence exposure or transfer outcome. |

## Required licensing decision before reuse

The Japanese Black record is internally inconsistent: its Zenodo API licence
field reports **CC BY 4.0**, while the record description says **CC
BY-NC-ND 4.0**. It is therefore **UNVERIFIED FOR REUSE**. Do not download,
redistribute, train a commercial model on, or publish derived artefacts from it
until the depositor/Zenodo record clarifies the licence in writing.

All other licence entries are source-record metadata, not legal advice. Keep a
copy of the record version, licence text, checksum and access date with any
locally downloaded data. Never commit raw participant- or animal-level data to
this repository; `data/raw/` is ignored by Git.

## Loader use

```powershell
vf-inspect                         # inspect data/raw
vf-inspect --candidates            # list the records above, with licences
vf-inspect path\to\file.csv --rows 3
```

```python
from vf_training.data_loaders import inspect_dataset, read_csv_rows

inspections = inspect_dataset("data/raw")  # returns what is actually there
rows = read_csv_rows("data/raw/example.csv", limit=5)
```

The functions return structured results and never print, so they are safe to use
in a script or a test. `vf-inspect` is the human-facing report: it prints every
file it finds and the actual CSV headers. A missing path raises
`FileNotFoundError`, and `vf-inspect` turns that into a `NOT FOUND` message with
exit code 2 rather than guessing file names or columns.
