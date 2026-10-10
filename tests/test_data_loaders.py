from pathlib import Path

import pytest

from vf_training.data_loaders import CANDIDATE_DATASETS, inspect_dataset, read_csv_rows


def test_local_csv_is_inspected_without_assumed_schema(tmp_path: Path) -> None:
    source = tmp_path / "observations.csv"
    source.write_text("actual_id,unexpected_label\n1,turn\n", encoding="utf-8")

    inspection = inspect_dataset(source)

    assert inspection[0].columns == ("actual_id", "unexpected_label")
    assert inspection[0].size_bytes == source.stat().st_size
    assert read_csv_rows(source) == [{"actual_id": "1", "unexpected_label": "turn"}]


def test_directory_inspection_reports_every_file_type(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("not tabular", encoding="utf-8")
    (tmp_path / "empty.csv").write_text("", encoding="utf-8")

    by_name = {item.path.name: item for item in inspect_dataset(tmp_path)}

    assert set(by_name) == {"notes.txt", "empty.csv"}
    assert by_name["notes.txt"].columns is None
    assert "format-specific reader" in by_name["notes.txt"].note
    # A CSV with no readable header is reported, not silently dropped.
    assert by_name["empty.csv"].columns is None
    assert "could not be read" in by_name["empty.csv"].note


def test_missing_dataset_raises_instead_of_reporting_empty(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inspect_dataset(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        read_csv_rows(tmp_path / "missing.csv")


def test_row_limit_and_header_requirements(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")

    assert len(read_csv_rows(source, limit=2)) == 2
    with pytest.raises(ValueError, match="limit must be at least one"):
        read_csv_rows(source, limit=0)

    headerless = tmp_path / "headerless.csv"
    headerless.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="No header row found"):
        read_csv_rows(headerless)


def test_licence_conflict_is_attached_to_the_blocked_record() -> None:
    """The dairy record is open; only the Japanese Black record is unresolved."""
    licences = {spec.key: spec.licence for spec in CANDIDATE_DATASETS}

    assert licences["zenodo_dairy_activity_location"] == "CC BY 4.0"
    assert licences["zenodo_japanese_black"].startswith("UNVERIFIED FOR REUSE")
    assert all(
        "UNVERIFIED" not in licence for key, licence in licences.items() if "japanese" not in key
    )
