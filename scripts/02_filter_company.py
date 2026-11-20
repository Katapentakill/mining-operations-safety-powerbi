"""Filter the nationwide MSHA tables to the mines of one company (config.toml) and write CSVs.

A company is the *current controller* of a mine in MSHA's Mines table. Event and workforce
tables are then filtered by MINE_ID, so a mine's full history since 2000 is included, also
the years in which another company controlled it (the model keeps a flag for that).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import pipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, help="output folder (default: data/csv/<slug>)")
    ap.add_argument("--no-manifest", action="store_true", help="do not touch data/manifest.json")
    args = ap.parse_args()

    cfg = common.load_config()
    raw = common.data_dir(cfg) / "raw" / "msha"
    slug = cfg["company"]["slug"]
    name = cfg["company"]["controller_name"]
    out = args.out or common.data_dir(cfg) / "csv" / slug

    mine_ids, ctrl_ids, skipped = pipeline.find_company_mines(raw / "Mines" / "Mines.txt", name)
    print(f"{name}: controlador(es) {sorted(ctrl_ids)}, {len(mine_ids)} minas")
    if skipped:
        print(f"AVISO: {skipped} filas de Mines.txt con numero de campos distinto se omitieron al buscar la empresa")

    rows = {}
    for table, meta in common.TABLES.items():
        n, rejected = pipeline.filter_table(raw / table / f"{table}.txt", out / meta["csv"], mine_ids)
        if rejected:
            print(f"ERROR {table}: {rejected} filas con numero de campos incorrecto; no se descartan en silencio")
            return 1
        rows[meta["csv"]] = n
        print(f"{meta['csv']:34} {n:>8,}")

    if not args.no_manifest:
        common.update_manifest(
            cfg,
            "company",
            {
                "slug": slug,
                "controller_name": name,
                "controller_ids": sorted(ctrl_ids),
                "mines": len(mine_ids),
                "output_dir": str(out),
                "rows": rows,
                "generated_at": common.utc_now(),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
