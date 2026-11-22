"""Data layer of the Excel workbook: runs excel/queries.sql inside the SQL Server container and returns pandas DataFrames.

It reuses the helpers of scripts/04_load_sqlserver.py (`read_env`, the sqlcmd command line) like tests/sql does, but runs docker with
an explicit UTF-8 decoding so accents in names survive on Windows.
"""
from __future__ import annotations

import importlib.util
import io
import re
import shlex
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QUERIES = Path(__file__).resolve().parent / "queries.sql"

_spec = importlib.util.spec_from_file_location("loader", ROOT / "scripts" / "04_load_sqlserver.py")
loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loader)


def read_queries(path: Path = QUERIES) -> dict[str, str]:
    """Split queries.sql into {name: sql} using the `-- name: xxx` markers."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def container_ready() -> bool:
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        return "sqlserver" in out.stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False


def run_query(sql: str) -> pd.DataFrame:
    """Execute one query in the container and parse sqlcmd's pipe-separated output."""
    env = loader.read_env()
    inner = loader.SQLCMD + " " + " ".join(
        shlex.quote(a) for a in ("-d", "MiningOpsSafety", "-s", "|", "-W", "-Q", "SET NOCOUNT ON;\n" + sql)
    )
    res = subprocess.run(
        ["docker", "compose", "exec", "-T", "-e", f"PBI_READER_PASSWORD={env.get('PBI_READER_PASSWORD', '')}",
         "sqlserver", "sh", "-c", inner],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    lines = [ln for ln in res.stdout.splitlines() if ln.strip() and not ln.startswith(("Changed database", "Warning:"))]
    if len(lines) < 2:
        return pd.DataFrame()
    # line 0 = header, line 1 = dashes underline, then the rows
    body = "\n".join([lines[0]] + lines[2:])
    df = pd.read_csv(io.StringIO(body), sep="|", skipinitialspace=True, keep_default_na=False)
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype(str).str.strip()  # some MSHA names carry a trailing space
    return df


def load_frames() -> dict[str, pd.DataFrame]:
    return {name: run_query(sql) for name, sql in read_queries().items()}
