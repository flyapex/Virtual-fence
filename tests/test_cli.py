"""Tests for the installed console entry points.

These call the same functions the ``vf-*`` commands call, so a broken command
line is caught here rather than by a user.
"""

from pathlib import Path

import pytest

from vf_training.cli import inspect_main, play_main, power_main, simulate_main


def test_simulate_main_prints_labelled_output(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = simulate_main(
        ["--arm", "simulation", "--tau", "0.6", "--animals", "2", "--days", "2"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "SIMULATED PLANNING OUTPUT" in output
    assert "arm=simulation" in output
    assert "first day of an 80%-for-2-days run" in output


def test_figure_flags_without_plot_are_refused() -> None:
    with pytest.raises(SystemExit, match="--compare-arms only affects the figure"):
        simulate_main(["--compare-arms"])
    with pytest.raises(SystemExit, match="--show only affects the figure"):
        simulate_main(["--show"])
    with pytest.raises(SystemExit, match="--show only affects the figure"):
        power_main(["--show"])


def test_power_main_reports_the_design_floor_and_both_zero_causes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = power_main(
        [
            "--groups-per-arm",
            "3",
            "4",
            "--taus",
            "0",
            "1",
            "--replications",
            "3",
            "--animals-per-group",
            "2",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Smallest attainable two-sided p by design: 3/arm 0.100, 4/arm 0.029." in output
    assert "cannot reject at alpha" in output
    assert "below the 30% target" in output


def test_inspect_main_lists_candidates_and_flags_the_unverified_licence(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = inspect_main(["--candidates"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "CANDIDATE CALIBRATION DATASETS" in output
    assert "UNVERIFIED FOR REUSE" in output
    # The dairy record is open; only the Japanese Black record is blocked.
    assert output.count("UNVERIFIED FOR REUSE") == 1


def test_inspect_main_reports_a_missing_path_and_an_empty_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert inspect_main([str(tmp_path / "missing")]) == 2
    assert "NOT FOUND" in capsys.readouterr().out

    assert inspect_main([str(tmp_path)]) == 1
    assert "NO FILES FOUND" in capsys.readouterr().out


def test_inspect_main_reads_local_headers_without_assuming_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "observations.csv"
    source.write_text("actual_id,unexpected_label\n1,turn\n2,walk\n", encoding="utf-8")

    exit_code = inspect_main([str(source), "--rows", "1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "actual_id" in output
    assert "READ 1 row(s)" in output


def test_play_main_requires_a_single_export_mode() -> None:
    with pytest.raises(SystemExit, match="either --gif or --still"):
        play_main(["--gif", "--still", "--days", "1", "--animals", "1"])


def test_play_main_writes_a_still_frame(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib", reason="playback needs the optional plots extra")

    exit_code = play_main(
        [
            "--days",
            "1",
            "--animals",
            "2",
            "--steps",
            "3",
            "--still",
            "--outdir",
            str(tmp_path),
            "--dpi",
            "60",
        ]
    )

    assert exit_code == 0
    assert list(tmp_path.glob("*_still.png"))
