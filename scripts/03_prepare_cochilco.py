"""Download the Cochilco Excel files (Chile copper price and production) and write tidy CSVs.

Context data only: Cochilco covers Chilean mines of all companies, not Freeport-McMoRan.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import pipeline  # noqa: E402


def main() -> int:
    cfg = common.load_config()
    raw = common.data_dir(cfg) / "raw" / "cochilco"
    out = common.data_dir(cfg) / "csv" / "chile_context"
    base = cfg["cochilco"]["base_url"]

    files = {}
    for local_name, rel in cfg["cochilco"]["files"].items():
        path = raw / local_name
        if not path.exists():
            print(f"descargando {local_name}")
            pipeline.download(f"{base}/{rel}", path, timeout=120)
        files[local_name] = {"bytes": path.stat().st_size, "sha256": common.sha256_of(path)}

    jobs = {
        "cu_price_monthly.csv": pipeline.tidy_price_monthly(raw / "precios-cobre-refinado-mensual.xlsx"),
        "cu_price_annual.csv": pipeline.tidy_price_annual(raw / "precios-cobre-refinado-anual.xlsx"),
        "cu_production_monthly.csv": pipeline.tidy_production_monthly(
            raw / "produccion-cobre-mina-por-empresa-mensual.xlsx"
        ),
        "cu_production_annual.csv": pipeline.tidy_production_annual(
            raw / "produccion-cobre-mina-por-empresa-anual.xlsx"
        ),
    }
    rows = {}
    for name, data in jobs.items():
        rows[name] = pipeline.write_csv(out / name, data)
        print(f"{name:28} {rows[name]:>7,}")

    last_prod = max(r["month"] for r in jobs["cu_production_monthly.csv"])
    last_price = max(r["month"] for r in jobs["cu_price_monthly.csv"])
    common.update_manifest(
        cfg,
        "cochilco",
        {"files": files, "rows": rows, "last_production_month": last_prod, "last_price_month": last_price},
    )
    print(f"ultimo mes de produccion: {last_prod} | ultimo mes de precio: {last_price}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
