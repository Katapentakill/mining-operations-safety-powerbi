"""Shared helpers: configuration, table catalog and the snapshot manifest."""
from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "msha-open-data-client/1.0"

# MSHA data set -> output CSV name and data-dictionary file (all under DataSets/)
TABLES = {
    "Mines": {"csv": "mines.csv", "definition": "Mines_Definition_File.txt"},
    "Accidents": {"csv": "accidents.csv", "definition": "Accidents_Definition_File.txt"},
    "Inspections": {"csv": "inspections.csv", "definition": "Inspections_Definition_File.txt"},
    "Violations": {"csv": "violations.csv", "definition": "violations_Definition_File.txt"},
    "AssessedViolations": {"csv": "assessed_violations.csv", "definition": "Assessed_Violations_Definition_File.txt"},
    "MinesProdYearly": {"csv": "mines_prod_yearly.csv", "definition": "MineSProdYearly_Definition_File.txt"},
    "MinesProdQuarterly": {"csv": "mines_prod_quarterly.csv", "definition": "MineSProdQuarterly_Definition_File.txt"},
    "ControllerOperatorHistory": {
        "csv": "controller_operator_history.csv",
        "definition": "Controller_Operator_History_Definition_File.txt",
    },
}


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def data_dir(cfg: dict) -> Path:
    return ROOT / cfg["paths"]["data_dir"]


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def manifest_path(cfg: dict) -> Path:
    return data_dir(cfg) / "manifest.json"


def read_manifest(cfg: dict) -> dict:
    p = manifest_path(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def update_manifest(cfg: dict, section: str, payload: dict) -> None:
    manifest = read_manifest(cfg)
    manifest[section] = payload
    manifest["updated_at"] = utc_now()
    p = manifest_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
