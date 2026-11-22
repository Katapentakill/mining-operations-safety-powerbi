"""The Excel generator: tiny synthetic data in, a workbook with the expected sheets, tables, formulas and charts out.

The last test compares the aggregates with the control totals of the database and is skipped when the container is not running.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "excel"))

import build_excel  # noqa: E402
import datos  # noqa: E402

openpyxl = pytest.importorskip("openpyxl")
pytest.importorskip("xlsxwriter")


@pytest.fixture()
def frames() -> dict[str, pd.DataFrame]:
    rows = []
    for mina, base in (("Mina Alfa", 10), ("Mina Beta", 4), ("Mina Gamma", 0)):
        for anio in (2000, 2001, 2002):
            rows.append({"mina": mina, "anio": anio, "accidentes": base + anio - 2000, "fatalidades": 1 if mina == "Mina Alfa" and anio == 2001 else 0,
                         "casos_tasa": base // 2, "dias_perdidos": 5, "infracciones": base * 2, "multa_pagada": 1000.0 * base, "horas": 200_000})
    anio_mina = pd.DataFrame(rows)
    gravedad = pd.DataFrame([
        {"mina": "Mina Alfa", "anio": 2001, "grupo": "Fatalidad", "orden": 1, "accidentes": 1},
        {"mina": "Mina Alfa", "anio": 2001, "grupo": "Con días perdidos", "orden": 2, "accidentes": 5},
        {"mina": "Mina Beta", "anio": 2001, "grupo": "Sin días perdidos", "orden": 3, "accidentes": 3},
        {"mina": "Mina Beta", "anio": 2002, "grupo": "Sin lesión u otros", "orden": 4, "accidentes": 2},
    ])
    minas = pd.DataFrame([
        {"mina": "Mina Alfa", "estado": "Arizona", "situacion": "Activa", "tipo": "Superficie", "empleados": 100},
        {"mina": "Mina Beta", "estado": "Colorado", "situacion": "Abandonada", "tipo": "Subterránea", "empleados": 0},
        {"mina": "Mina Gamma", "estado": "Oregón", "situacion": "Activa", "tipo": "Superficie", "empleados": 5},
    ])
    return {"anio_mina": anio_mina, "gravedad": gravedad, "minas": minas}


def test_queries_file_defines_every_block():
    assert set(datos.read_queries()) == {"anio_mina", "gravedad", "minas", "control"}
    assert all("rpt." in sql for sql in datos.read_queries().values())  # only the reporting views, like Power BI


def test_workbook_structure(tmp_path, frames):
    out = tmp_path / "libro.xlsx"
    summary = build_excel.build_workbook(frames, out, snapshot="2026-11-19")
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Inicio", "Panel", "Minas", "Datos", "Pivote", "Cómo está hecho", "Calc"]
    assert set(wb["Datos"].tables) == {"t_anio_mina", "t_gravedad", "t_minas"}
    assert {"selAnio", "selMina", "yMin", "yMax", "critMina"} <= set(wb.defined_names)
    panel = wb["Panel"]
    assert len(panel.data_validations.dataValidation) == 2  # year and mine drop-downs
    assert len(panel._charts) == 4
    # XlsxWriter stores XLOOKUP as a dynamic-array formula; openpyxl returns it as an ArrayFormula object with the text in `.text`
    formulas = [getattr(c.value, "text", c.value) for row in panel.iter_rows() for c in row]
    formulas = [f for f in formulas if isinstance(f, str) and f.startswith("=")]
    assert any("SUMIFS" in f for f in formulas) and any("XLOOKUP" in f for f in formulas)
    assert summary["accidentes"] == int(frames["anio_mina"]["accidentes"].sum())


def test_default_selection_values_and_rate(tmp_path, frames):
    s = build_excel.build_workbook(frames, tmp_path / "a.xlsx", "Todos", "Todas", snapshot="x")
    a = frames["anio_mina"]
    assert s["tasa"] == pytest.approx(a["casos_tasa"].sum() * 200000 / a["horas"].sum())
    one = build_excel.build_workbook(frames, tmp_path / "b.xlsx", 2001, "Mina Alfa", snapshot="x")
    sub = a[(a.anio == 2001) & (a.mina == "Mina Alfa")]
    assert one["accidentes"] == int(sub["accidentes"].sum()) and one["fatalidades"] == 1
    assert one["top"][0][0] == "Mina Alfa"  # the top 5 ignores the mine selector but follows the year


def test_cached_formula_values_are_written(tmp_path, frames):
    out = tmp_path / "c.xlsx"
    build_excel.build_workbook(frames, out, snapshot="x")
    wb = openpyxl.load_workbook(out, data_only=True)
    card = wb["Panel"]["B8"].value  # accidents card, cached result of the formula
    assert card == int(frames["anio_mina"]["accidentes"].sum())


@pytest.mark.skipif(not datos.container_ready(), reason="SQL Server container is not running")
def test_aggregates_match_database_control_totals():
    f = datos.load_frames()
    c = f["control"].iloc[0]
    a = f["anio_mina"]
    assert int(a["accidentes"].sum()) == int(c["accidentes"])
    assert int(a["fatalidades"].sum()) == int(c["fatalidades"])
    assert int(a["infracciones"].sum()) == int(c["infracciones"])
    assert float(a["multa_pagada"].sum()) == pytest.approx(float(c["multa_pagada"]))
    assert int(a["horas"].sum()) == int(c["horas"])
    assert int(f["gravedad"]["accidentes"].sum()) == int(c["accidentes"])
    assert f["minas"]["mina"].is_unique  # duplicate MSHA names are told apart by mine id
