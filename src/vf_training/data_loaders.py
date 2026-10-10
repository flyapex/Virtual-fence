"""Cautious local inspection helpers for candidate calibration datasets.

The project deliberately does not download study data. Place data obtained from
the official source in ``data/raw`` and inspect it first. These utilities derive
headers from the actual file rather than baking unverified schemas into code.

The helpers here return what they find and never print: reporting is the job of
the ``vf-inspect`` command, which is also available as
``python scripts/inspect_datasets.py``.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSpec:
    """Verified source metadata, not a promise that a local download exists."""

    key: str
    title: str
    record_url: str
    licence: str
    published_size_bytes: int
    intended_use: str = "Calibration and workflow development only; not transfer evidence."


# Metadata were checked against each source record on 2026-10-10. File schemas
# are intentionally not hard-coded: use inspect_dataset() on the downloaded files.
CANDIDATE_DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        "zenodo_gnss_39",
        "Calculating animal distribution evenness metrics from GNSS tracking data",
        "https://zenodo.org/records/17338610",
        "CC BY 4.0",
        2_193_477,
    ),
    DatasetSpec(
        "usda_virtual_fence",
        "Data from: Visual cues improve awareness but decrease compliance to virtual fence in cattle",
        "https://doi.org/10.15482/USDA.ADC/30888611",
        "CC0 1.0",
        6_036_302,
    ),
    DatasetSpec(
        "figshare_beef_behaviour",
        "Labeled sensor dataset of beef cattle behavior grazing desert rangelands",
        "https://figshare.com/articles/dataset/28801181",
        "CC BY 4.0",
        474_992,
    ),
    DatasetSpec(
        "zenodo_dairy_activity_location",
        "Time Series of Dairy Cow Activity and Barn Area Use",
        "https://zenodo.org/records/14886594",
        "CC BY 4.0",
        79_918_291,
    ),
    DatasetSpec(
        "zenodo_japanese_black",
        "Japanese Black Beef Cow Behavior Classification Dataset",
        "https://zenodo.org/records/5849025",
        # The record contradicts itself; see docs/datasets.md before any reuse.
        "UNVERIFIED FOR REUSE: Zenodo API reports CC BY 4.0, the record description says CC BY-NC-ND 4.0",
        14_460_415,
    ),
)


@dataclass(frozen=True)
class FileInspection:
    """A non-assumptive description of one locally available file."""

    path: Path
    size_bytes: int
    columns: tuple[str, ...] | None
    note: str


def _csv_columns(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
    if not header:
        raise ValueError(f"No CSV header found in {path}")
    return tuple(header)


def inspect_dataset(path: str | Path) -> tuple[FileInspection, ...]:
    """Describe the files at `path` using what each file actually contains.

    A file path is inspected directly; a directory path is searched recursively.
    Unsupported file types are still reported, so nothing is silently discarded.
    Raises ``FileNotFoundError`` when the path does not exist, rather than
    reporting an empty result that could be mistaken for "no data there".
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"No such file or directory: {root}")
    candidates: Iterable[Path] = (
        (root,) if root.is_file() else sorted(item for item in root.rglob("*") if item.is_file())
    )

    inspections: list[FileInspection] = []
    for file_path in candidates:
        size_bytes = file_path.stat().st_size
        if file_path.suffix.lower() == ".csv":
            try:
                columns = _csv_columns(file_path)
            except (OSError, UnicodeError, ValueError, csv.Error) as error:
                columns = None
                note = f"CSV present but header could not be read: {error}"
            else:
                note = "CSV header read from the local file"
        else:
            columns = None
            note = "Present; inspect with a format-specific reader if needed"
        inspections.append(
            FileInspection(
                path=file_path,
                size_bytes=size_bytes,
                columns=columns,
                note=note,
            )
        )
    return tuple(inspections)


def read_csv_rows(path: str | Path, *, limit: int | None = None) -> list[dict[str, str]]:
    """Read a local CSV using its own header, with a transparent optional limit.

    Returns every row by default. Raises ``FileNotFoundError`` for a missing
    file and ``ValueError`` for a file without a header row or a limit below one.
    """
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least one when given.")
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError(f"No header row found in {file_path}")
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=1):
            rows.append(dict(row))
            if limit is not None and row_number >= limit:
                break
    return rows
