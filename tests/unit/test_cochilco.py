"""Unit tests for the Cochilco Excel parsers, using small workbooks built on the fly."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl
import pytest

import pipeline


def _book(path: Path, rows: list[list], sheet: str = "Hoja1") -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


def test_price_monthly_parses_dates_and_not_available(tmp_path: Path):
    p = _book(
        tmp_path / "price.xlsx",
        [
            ["Comision Chilena del Cobre"],
            ["MES - AÑO", "BML (cUS$/lb)", "COMEX (cUS$/lb)"],
            [dt.datetime(1960, 1, 1), 32.45, "N.D."],
            [dt.datetime(2024, 12, 1), 404.583, 410.843],
            [None, None, None],
            ["N.D. Informacion no disponible"],
        ],
    )
    rows = pipeline.tidy_price_monthly(p)
    assert rows == [
        {"month": "1960-01-01", "bml_cusd_lb": 32.45, "comex_cusd_lb": None},
        {"month": "2024-12-01", "bml_cusd_lb": 404.583, "comex_cusd_lb": 410.843},
    ]


def test_price_annual_keeps_integer_years_only(tmp_path: Path):
    p = _book(tmp_path / "pa.xlsx", [["AÑO", "BML", "COMEX"], [1935, 6.973, "N.D."], [None, None, None]])
    assert pipeline.tidy_price_annual(p) == [{"year": 1935, "bml_cusd_lb": 6.973, "comex_cusd_lb": None}]


def test_production_monthly_flags_aggregates_and_drops_placeholder_months(tmp_path: Path):
    header = ["mes-año ", "Chuquicamata", "Total Codelco", "Escondida", "TOTAL CHILE"]
    p = _book(
        tmp_path / "prod.xlsx",
        [
            ["title"],
            [None],
            header,
            [dt.datetime(2024, 1, 1), 21.5, 21.5, 87.9, 109.4],
            [dt.datetime(2026, 12, 1), 0, 0, 0, 0],  # future month filled with zeros: dropped
            ["2024", None, None, None, None],  # year label row: ignored
        ],
    )
    # the header row is found by its first cell, not by position
    rows = pipeline.tidy_production_monthly(p)
    by_faena = {r["faena"]: r for r in rows}
    assert set(by_faena) == {"Chuquicamata", "Total Codelco", "Escondida", "TOTAL CHILE"}
    assert by_faena["Total Codelco"]["is_aggregate"] == 1
    assert by_faena["TOTAL CHILE"]["is_aggregate"] == 1
    assert by_faena["Escondida"]["is_aggregate"] == 0
    assert {r["month"] for r in rows} == {"2024-01-01"}


def test_production_monthly_non_aggregates_sum_to_total(tmp_path: Path):
    header = ["mes-año", "Chuquicamata", "Radomiro Tomic", "Chuqui y R.Tomic", "Escondida", "TOTAL CHILE"]
    p = _book(tmp_path / "prod2.xlsx", [header, [dt.datetime(2024, 1, 1), 20.0, 10.0, 30.0, 70.0, 100.0]])
    rows = pipeline.tidy_production_monthly(p)
    non_agg = sum(r["kt_fine_cu"] for r in rows if not r["is_aggregate"])
    total = next(r["kt_fine_cu"] for r in rows if r["faena"] == "TOTAL CHILE")
    assert non_agg == pytest.approx(total)


def test_production_annual_cleans_footnote_markers(tmp_path: Path):
    p = _book(
        tmp_path / "pan.xlsx",
        [
            ["Produccion", "Unidad", 1960, 1961],
            ["Chuquicamata (1)", "Miles TM", 231.1, "-"],
            ["Total Chile", "Miles TM", 500.0, 510.0],
            ["Notas:", None, None, None],
        ],
    )
    rows = pipeline.tidy_production_annual(p)
    assert {"year": 1960, "faena": "Chuquicamata", "is_aggregate": 0, "kt_fine_cu": 231.1} in rows
    assert all(r["faena"] != "Chuquicamata" or r["year"] == 1960 for r in rows)  # "-" is skipped
    assert any(r["faena"] == "Total Chile" and r["is_aggregate"] == 1 for r in rows)
