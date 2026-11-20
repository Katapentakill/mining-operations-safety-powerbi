"""Unit tests for the MSHA filtering functions (no network, no database)."""
from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import pytest

import pipeline


def test_read_header_strips_quotes_and_sum_wrapper(msha_dir: Path):
    hdr = pipeline.read_header(msha_dir / "Accidents" / "Accidents.txt")
    assert hdr == ["MINE_ID", "DOCUMENT_NO", "HOURS", "NARRATIVE"]


def test_find_company_mines_returns_only_that_controller(msha_dir: Path):
    mine_ids, ctrl_ids, skipped = pipeline.find_company_mines(msha_dir / "Mines" / "Mines.txt", "Acme Copper Inc")
    assert mine_ids == {"0200001", "0200002"}
    assert ctrl_ids == {"C1"}
    assert skipped == 0


def test_find_company_mines_unknown_company_suggests_similar_names(msha_dir: Path):
    with pytest.raises(ValueError, match="Acme Copper Inc"):
        pipeline.find_company_mines(msha_dir / "Mines" / "Mines.txt", "Acme Mining")


def test_filter_table_keeps_company_rows_and_counts_rejects(msha_dir: Path, tmp_path: Path):
    out = tmp_path / "out" / "accidents.csv"
    ok, rejected = pipeline.filter_table(msha_dir / "Accidents" / "Accidents.txt", out, {"0200001", "0200002"})
    assert (ok, rejected) == (2, 1)  # D1 and D3 kept, D4 has too many fields, D2 is another company
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig", newline="")))
    assert [r["DOCUMENT_NO"] for r in rows] == ["D1", "D3"]
    assert rows[0]["NARRATIVE"] == "Slipped, fell"  # comma survives thanks to CSV quoting
    assert rows[1]["NARRATIVE"] == "café break"  # latin-1 source is re-encoded as UTF-8


def test_filter_table_writes_bom_for_excel_and_power_bi(msha_dir: Path, tmp_path: Path):
    out = tmp_path / "accidents.csv"
    pipeline.filter_table(msha_dir / "Accidents" / "Accidents.txt", out, {"0200001"})
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    assert pipeline.count_csv_rows(out) == 1


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)


def test_load_file_is_utf16_pipe_delimited_and_keeps_accents(tmp_path: Path):
    src, dst = tmp_path / "a.csv", tmp_path / "load" / "a.txt"
    _write_csv(src, [["ID", "TEXT"], ["1", "café ¼ ½, with comma"], ["2", ""]])
    assert pipeline.csv_to_load_file(src, dst) == 2
    raw = dst.read_bytes()
    assert raw.startswith(b"\xff\xfe")  # UTF-16 LE byte order mark
    assert raw[2:].decode("utf-16-le") == "ID|TEXT\n1|café ¼ ½, with comma\n2|\n"


def test_load_file_rejects_values_that_would_break_the_format(tmp_path: Path):
    for bad in ("a|b", "line\nbreak"):
        src = tmp_path / "bad.csv"
        _write_csv(src, [["ID", "TEXT"], ["1", bad]])
        with pytest.raises(ValueError, match="pipe or a line break"):
            pipeline.csv_to_load_file(src, tmp_path / "bad.txt")


def test_extract_zip_rejects_path_traversal(tmp_path: Path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.txt", "x")
    with pytest.raises(ValueError, match="unsafe"):
        pipeline.extract_zip(bad, tmp_path / "dest")
    assert not (tmp_path / "evil.txt").exists()


def test_extract_zip_extracts_into_own_folder(tmp_path: Path):
    good = tmp_path / "Mines.zip"
    with zipfile.ZipFile(good, "w") as z:
        z.writestr("Mines.txt", "MINE_ID\r\n1\r\n")
    names = pipeline.extract_zip(good, tmp_path / "Mines")
    assert names == ["Mines.txt"]
    assert (tmp_path / "Mines" / "Mines.txt").exists()
