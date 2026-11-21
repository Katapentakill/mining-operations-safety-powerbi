"""Static checks on the Power BI project (PBIP) files. Used by CI; needs no Power BI Desktop.

1. every JSON file parses; forbidden files (cache.abf, localSettings.json, .pbix, .pbit) are absent
2. every TMDL file starts with a known keyword
3. model consistency: relationships point to existing tables and columns, DAX only references
   existing columns and measures, and every sourceColumn exists in the warehouse DDL (sql/02_dwh_tables.sql)
4. report consistency: every visual field points to an existing column or measure
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "powerbi"
FORBIDDEN = {"cache.abf", "localSettings.json"}
FORBIDDEN_SUFFIX = {".pbix", ".pbit"}
JSON_SUFFIX = {".json", ".pbip", ".pbir", ".platform", ".pbism"}
TMDL_START = ("model", "table", "relationship", "expression", "database", "culture", "cultureInfo", "perspective",
              "role", "ref", "createOrReplace", "///", "//", "annotation", "dataSource")


AUTO_DATE = ("LocalDateTable_", "DateTableTemplate_")


def unq(name: str) -> str:
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") and name.endswith("'") else name


def parse_tables(model_dir: Path) -> dict:
    """{table: {'view': str, 'columns': {display: source}, 'measures': {name: dax}}}"""
    out = {}
    for f in sorted((model_dir / "tables").glob("*.tmdl")):
        table = None
        cur = None
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("table "):
                table = unq(line[6:])
                if table.startswith(AUTO_DATE):  # tables Desktop generates for auto date/time: not ours to check
                    table = None
                    continue
                out[table] = {"view": None, "columns": {}, "measures": {}}
            elif table is None:
                continue
            elif m := re.match(r"^\tcolumn (.+)$", line):
                cur = ("column", unq(m.group(1)))
                out[table]["columns"][cur[1]] = None
            elif m := re.match(r"^\tmeasure ('(?:[^']|'')+'|\S+) =(?: (.*))?$", line):
                # Desktop writes short expressions inline ("measure X = expr"); hand-written ones sit on the next lines
                cur = ("measure", unq(m.group(1)))
                out[table]["measures"][cur[1]] = [m.group(2).strip()] if m.group(2) else []
            elif line.startswith("\t\t\t") and cur and cur[0] == "measure":
                out[table]["measures"][cur[1]].append(line.strip())
            elif m := re.match(r"^\t\tsourceColumn: (.+)$", line):
                out[table]["columns"][cur[1]] = m.group(1).strip()
            elif m := re.search(r'Item="([^"]+)"', line):
                out[table]["view"] = m.group(1)
    return out


def ddl_columns(sql: str) -> dict:
    cols = {}
    for m in re.finditer(r"CREATE TABLE dwh\.(\w+)\s*\((.*?)\)\s*;", sql, re.S):
        body, depth, buf, parts = re.sub(r"--[^\n]*", "", m.group(2)), 0, "", []  # drop comments (they may contain commas)
        for ch in body:
            depth += ch == "("
            depth -= ch == ")"
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        parts.append(buf)
        names = set()
        for p in parts:
            p = re.sub(r"--.*", "", p).strip()
            w = p.split()
            if w and w[0].upper() not in {"CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN"}:
                names.add(w[0].strip("[]"))
        cols[m.group(1)] = names
    return cols


def check_model(errors: list[str]) -> dict:
    model_dir = next(PBI.glob("*.SemanticModel")) / "definition"
    tables = parse_tables(model_dir)
    ddl = ddl_columns((ROOT / "sql" / "02_dwh_tables.sql").read_text(encoding="utf-8"))
    for t, spec in tables.items():
        view = spec["view"]
        src = ddl.get(view)
        if src is None:
            errors.append(f"table {t}: view {view!r} is not defined in sql/02_dwh_tables.sql")
            continue
        for disp, sc in spec["columns"].items():
            if sc is None or sc not in src:
                errors.append(f"table {t}: column {disp!r} has sourceColumn {sc!r} that is not in dwh.{view}")
    names_measures = {m for s in tables.values() for m in s["measures"]}
    rel = (model_dir / "relationships.tmdl").read_text(encoding="utf-8")
    for m in re.finditer(r"(?:from|to)Column: (\S+?)\.(.+)$", rel, re.M):
        t, c = unq(m.group(1)), unq(m.group(2))
        if t.startswith(AUTO_DATE):
            continue
        if t not in tables or c not in tables[t]["columns"]:
            errors.append(f"relationship points to missing column {t}.{c}")
    for t, spec in tables.items():
        for mname, lines in spec["measures"].items():
            dax = " ".join(lines)
            for rt, rc in re.findall(r"('[^']+'|\b[A-Za-z_]\w*)\[([^\]]+)\]", dax):
                rt = unq(rt)
                if rt not in tables or (rc not in tables[rt]["columns"] and rc not in tables[rt]["measures"]):
                    errors.append(f"measure {mname!r}: reference {rt}[{rc}] does not exist")
            for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", dax):
                if ref not in names_measures:
                    errors.append(f"measure {mname!r}: [{ref}] is not a measure")
    return tables


def check_report(tables: dict, errors: list[str]) -> int:
    n = 0
    for f in PBI.rglob("visual.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        # navigator, text boxes and shapes have no query: nothing to check
        query = data["visual"].get("query", {})
        fields = [pr["field"] for role in query.get("queryState", {}).values() for pr in role["projections"]]
        fields += [s["field"] for s in query.get("sortDefinition", {}).get("sort", [])]
        for field in fields:
            (kind, body), = field.items()
            if kind == "Aggregation":  # e.g. Average of a column on a scatter axis
                (kind, body), = body["Expression"].items()
            ent, prop = body["Expression"]["SourceRef"]["Entity"], body["Property"]
            pool = tables.get(ent, {}).get("measures" if kind == "Measure" else "columns", {})
            if prop not in pool:
                errors.append(f"{f.relative_to(ROOT)}: {kind} {ent}[{prop}] does not exist")
            n += 1
    return n


def check_layout(errors: list[str]) -> None:
    """Chrome (sidebar, header, slicer, navigator) must sit in the exact same place on every page."""
    seen: dict[str, tuple] = {}
    for f in sorted(PBI.rglob("visual.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        name = data["name"]
        if not name.startswith(("top_", "cab_", "nav_", "filtro_anio")):
            continue
        pos = data["position"]
        box = (pos["x"], pos["y"], pos["width"], pos["height"])
        first = seen.setdefault(name, box)
        if box != first:
            errors.append(f"{f.relative_to(ROOT)}: {name} at {box}, other pages use {first}")


def main() -> int:
    if not PBI.exists():
        print("powerbi/ not found: nothing to validate yet")
        return 0
    errors: list[str] = []
    for p in sorted(PBI.rglob("*")):
        if p.is_dir() or ".pbi" in p.parts:  # .pbi holds Desktop's local cache; .gitignore keeps it out of Git
            continue
        rel = p.relative_to(ROOT)
        if p.name in FORBIDDEN or p.suffix in FORBIDDEN_SUFFIX:
            errors.append(f"{rel}: must not be committed")
        elif p.suffix in JSON_SUFFIX:
            try:
                json.loads(p.read_text(encoding="utf-8-sig"))
            except ValueError as e:
                errors.append(f"{rel}: invalid JSON ({e})")
        elif p.suffix == ".tmdl":
            text = p.read_text(encoding="utf-8-sig").lstrip()
            if not text:
                errors.append(f"{rel}: empty TMDL file")
            elif not text.startswith(TMDL_START):
                errors.append(f"{rel}: unexpected first token {text.split()[0]!r}")
    tables = check_model(errors)
    fields = check_report(tables, errors)
    check_layout(errors)
    for e in errors:
        print("ERROR", e)
    n_meas = sum(len(t["measures"]) for t in tables.values())
    print(f"{'FAILED' if errors else 'ok'}: {len(errors)} problem(s); {len(tables)} tables, {n_meas} measures, {fields} visual fields checked")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
