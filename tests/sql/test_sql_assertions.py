"""Run every tests/sql/*.sql inside the SQL Server container; a check fails when its query returns rows.

Skipped automatically when the container is not running, so `pytest` also works without Docker.
In CI the container is started with the small fixture data set.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("loader", ROOT / "scripts" / "04_load_sqlserver.py")
loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loader)


def _container_ready() -> bool:
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        return "sqlserver" in out.stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False


pytestmark = pytest.mark.skipif(not _container_ready(), reason="SQL Server container is not running")


@pytest.mark.parametrize("sql_file", sorted(SQL_DIR.glob("0*.sql")), ids=lambda p: p.stem)
def test_sql_assertions(sql_file: Path):
    env = loader.read_env()
    cfg = loader.common.load_config()
    res = loader.sqlcmd(
        env, cfg["company"]["slug"], "-h", "-1", "-W", "-s", " | ", "-i", f"/tests/{sql_file.name}", capture=True
    )
    noise = ("Changed database context", "Warning:")
    failures = [
        ln for ln in res.stdout.splitlines()
        if ln.strip() and not ln.startswith(noise) and "rows affected" not in ln
    ]
    assert not failures, "failed checks:\n" + "\n".join(failures)
