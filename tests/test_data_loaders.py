from vf_training.data_loaders import inspect_dataset, read_csv_rows


def test_local_csv_is_inspected_without_assumed_schema(tmp_path) -> None:
    source = tmp_path / "observations.csv"
    source.write_text("actual_id,unexpected_label\n1,turn\n", encoding="utf-8")
    inspection = inspect_dataset(source)
    assert inspection[0].columns == ("actual_id", "unexpected_label")
    assert read_csv_rows(source) == [{"actual_id": "1", "unexpected_label": "turn"}]


def test_missing_dataset_fails_gracefully(tmp_path) -> None:
    assert inspect_dataset(tmp_path / "missing") == ()

