"""Cautious local inspection helpers for candidate calibration datasets.

The project deliberately does not download study data. Place data obtained from
the official source in ``data/raw`` and inspect it first. These utilities derive
headers from the actual file rather than baking unverified schemas into code.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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
        "CONFLICT: API says CC BY 4.0; record description says CC BY-NC-ND 4.0",
        79_918_291,
    ),
    DatasetSpec(
        "zenodo_japanese_black",
        "Japanese Black Beef Cow Behavior Classification Dataset",
        "https://zenodo.org/records/5849025",
        "CC BY 4.0",
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
    """Print discovered files and actual CSV headers; never guess a schema.

    A file path is inspected directly. A directory path is searched recursively.
    Unsupported file types are still reported so users can decide how to inspect
    them; this function does not silently discard them.
    """
    root = Path(path)
    if not root.exists():
        print(f"NOT FOUND: {root}")
        return ()
    files: Iterable[Path] = (root,) if root.is_file() else sorted(item for item in root.rglob("*") if item.is_file())
    inspections: list[FileInspection] = []
    for file_path in files:
        if file_path.suffix.lower() == ".csv":
            try:
                columns = _csv_columns(file_path)
                note = "CSV header read from local file"
                print(f"FOUND CSV: {file_path} ({file_path.stat().st_size} bytes); columns: {columns}")
            except (OSError, UnicodeError, ValueError, csv.Error) as error:
                columns = None
                note = f"CSV present but header could not be read: {error}"
                print(f"FOUND CSV WITH READ ERROR: {file_path}; {error}")
        else:
            columns = None
            note = "Present; inspect with a format-specific reader if needed"
            print(f"FOUND {file_path.suffix or 'file'}: {file_path} ({file_path.stat().st_size} bytes)")
        inspections.append(
            FileInspection(
                path=file_path,
                size_bytes=file_path.stat().st_size,
                columns=columns,
                note=note,
            )
        )
    if not inspections:
        print(f"NO FILES FOUND: {root}")
    return tuple(inspections)


def read_csv_rows(path: str | Path, *, limit: int | None = None) -> list[dict[str, str]]:
    """Read a local CSV using its own header, with a transparent optional limit."""
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("No header row found")
            rows: list[dict[str, str]] = []
            for row_number, row in enumerate(reader, start=1):
                rows.append(dict(row))
                if limit is not None and row_number >= limit:
                    break
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"CSV LOAD FAILED: {file_path}; {error}")
        return []
    print(f"LOADED {len(rows)} row(s) from {file_path}; columns found: {tuple(reader.fieldnames)}")
    return rows

