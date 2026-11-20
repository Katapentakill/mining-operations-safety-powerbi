"""The committed Power BI project must be internally consistent (model, DDL, DAX and report fields)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("validate_pbip", ROOT / "scripts" / "validate_pbip.py")
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)


def test_powerbi_project_is_consistent(capsys):
    assert validate.main() == 0, capsys.readouterr().out


def test_ddl_parser_ignores_comments_with_commas():
    sql = "CREATE TABLE dwh.t (\n  a INT NOT NULL, -- note, with a comma\n  b INT NULL\n);"
    assert validate.ddl_columns(sql) == {"t": {"a", "b"}}


def test_unquote_handles_escaped_apostrophes():
    assert validate.unq("'Año-Mes'") == "Año-Mes"
    assert validate.unq("'it''s'") == "it's"
    assert validate.unq("Fecha") == "Fecha"
