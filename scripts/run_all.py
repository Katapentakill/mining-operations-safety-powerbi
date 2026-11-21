"""Run the whole pipeline: download, filter, staging DDL, SQL Server load.

Usage: python scripts/run_all.py [--skip-download]
Requires Docker and a .env file (copy .env.example).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, *extra: str) -> None:
    print(f"\n=== {script}")
    subprocess.run([sys.executable, str(HERE / script), *extra], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-download", action="store_true", help="reuse the zips already in data/raw")
    args = ap.parse_args()

    if not args.skip_download:
        run("01_download_msha.py")
    run("02_filter_company.py")
    run("generate_staging_ddl.py")
    run("04_load_sqlserver.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
