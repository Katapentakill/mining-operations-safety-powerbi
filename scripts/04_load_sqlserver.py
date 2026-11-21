"""Start SQL Server (Docker Compose), create the database objects if needed and load the CSV files.

The first run creates everything (sql/00 to 06). Later runs only reload staging and rerun the ETL
(sql/10 and 11). Use --reinit to drop and recreate the tables.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SQLCMD = "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P \"$MSSQL_SA_PASSWORD\" -b -I"
INIT_SCRIPTS = [
    "00_database.sql",
    "01_staging.sql",
    "02_dwh_tables.sql",
    "03_etl.sql",
    "04_views_rpt.sql",
    "05_indexes.sql",
    "06_security.sql",
]
LOAD_SCRIPTS = ["10_load_staging.sql", "11_run_etl.sql"]


def prepare_load_files(slug: str) -> None:
    """Write the UTF-16 pipe-delimited copies that BULK INSERT reads (data/load, mounted in the container)."""
    import os

    import pipeline

    base = common.ROOT / os.environ.get("CSV_DIR", str(common.data_dir(common.load_config()) / "csv"))
    load = common.data_dir(common.load_config()) / "load"
    jobs = [(base / slug / meta["csv"], load / slug / (meta["csv"][:-4] + ".txt")) for meta in common.TABLES.values()]
    for src, dst in jobs:
        pipeline.csv_to_load_file(src, dst)
    print(f"-> {len(jobs)} load files written to {load}")


def read_env() -> dict[str, str]:
    path = common.ROOT / ".env"
    if not path.exists():
        raise SystemExit("Falta el archivo .env: copia .env.example a .env y cambia las contrasenas.")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def compose(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["docker", "compose", *args], cwd=common.ROOT, check=True, text=True, capture_output=capture
        )
    except subprocess.CalledProcessError as e:
        # Show what sqlcmd/docker printed, but never the command line (it carries passwords).
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        raise SystemExit(f"docker compose {args[0]} failed with exit code {e.returncode}") from None


def sqlcmd(env: dict[str, str], slug: str, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
    inner = SQLCMD + " " + " ".join(shlex.quote(a) for a in args)
    return compose(
        "exec", "-T",
        "-e", f"PBI_READER_PASSWORD={env.get('PBI_READER_PASSWORD', '')}",
        "-e", f"COMPANY_SLUG={slug}",
        "sqlserver", "sh", "-c", inner,
        capture=capture,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="company folder under data/csv (default: config.toml)")
    ap.add_argument("--reinit", action="store_true", help="drop and recreate the database objects")
    ap.add_argument("--skip-up", action="store_true", help="do not run docker compose up")
    ap.add_argument("--reset-db", action="store_true", help="drop the MiningOpsSafety database first (then reinit)")
    args = ap.parse_args()

    cfg = common.load_config()
    slug = args.slug or cfg["company"]["slug"]
    env = read_env()
    prepare_load_files(slug)

    if not args.skip_up:
        compose("up", "-d", "--wait")

    if args.reset_db:
        print("-> dropping database MiningOpsSafety")
        sqlcmd(
            env, slug, "-Q",
            "IF DB_ID(N'MiningOpsSafety') IS NOT NULL BEGIN "
            "ALTER DATABASE MiningOpsSafety SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
            "DROP DATABASE MiningOpsSafety; END",
        )

    probe = (
        "SET NOCOUNT ON; SELECT CASE WHEN DB_ID(N'MiningOpsSafety') IS NULL THEN 0 "
        "WHEN OBJECT_ID(N'MiningOpsSafety.dwh.usp_load_all') IS NULL THEN 0 ELSE 1 END"
    )
    res = sqlcmd(env, slug, "-h", "-1", "-W", "-Q", probe, capture=True)
    initialized = res.stdout.strip().splitlines()[-1].strip() == "1"

    if args.reinit or not initialized:
        for name in INIT_SCRIPTS:
            print(f"-> {name}")
            sqlcmd(env, slug, "-i", f"/sql/{name}")
    for name in LOAD_SCRIPTS:
        print(f"-> {name} (company folder: {slug})")
        out = sqlcmd(env, slug, "-i", f"/sql/{name}", capture=True)
        if out.stdout.strip():
            print(out.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
