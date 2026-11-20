"""Download the MSHA open-data sets listed in common.TABLES and extract each in its own folder.

Idempotent: existing zips are kept (use --force to download again). The remote size is
compared with the local zip so a stale snapshot is reported, never silently replaced.
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
    ap.add_argument("--force", action="store_true", help="download again even if the zip exists")
    args = ap.parse_args()

    cfg = common.load_config()
    base = cfg["msha"]["base_url"]
    raw = common.data_dir(cfg) / "raw" / "msha"
    entries = {}
    for name, meta in common.TABLES.items():
        url = f"{base}/{name}.zip"
        zpath = raw / "zips" / f"{name}.zip"
        remote = None
        try:
            remote = pipeline.remote_info(url)
        except OSError as e:
            if not zpath.exists():
                raise
            print(f"AVISO {name}: no se pudo consultar el servidor ({e}); se usa el zip local")

        if args.force or not zpath.exists():
            print(f"descargando {name}" + (f" ({remote['bytes'] / 1e6:.1f} MB)" if remote else ""))
            pipeline.download(url, zpath)
        elif remote and zpath.stat().st_size != remote["bytes"]:
            print(
                f"AVISO {name}: el zip local ({zpath.stat().st_size:,} B) difiere del remoto "
                f"({remote['bytes']:,} B). MSHA actualiza cada viernes; usa --force para refrescar."
            )

        dest = raw / name
        if dest.exists() and any(dest.iterdir()):
            members = sorted(p.name for p in dest.iterdir())
        else:
            members = pipeline.extract_zip(zpath, dest)

        definition = raw / "definiciones" / meta["definition"]
        if not definition.exists():
            pipeline.download(f"{base}/{meta['definition']}", definition, timeout=60)

        entries[name] = {
            "url": url,
            "zip_bytes": zpath.stat().st_size,
            "zip_sha256": common.sha256_of(zpath),
            "remote_last_modified": remote["last_modified"] if remote else None,
            "members": members,
            "definition_file": meta["definition"],
        }
        print(f"ok {name}")

    common.update_manifest(cfg, "msha", {"base_url": base, "checked_at": common.utc_now(), "sets": entries})
    print(f"manifiesto actualizado: {common.manifest_path(cfg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
