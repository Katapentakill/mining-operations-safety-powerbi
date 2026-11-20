"""Pure data functions used by the ingestion CLIs (and by the tests)."""
from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

from common import USER_AGENT

# ---------------------------------------------------------------- HTTP / zip


def _request(url: str, method: str = "GET") -> urllib.request.Request:
    return urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})


def remote_info(url: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(_request(url, "HEAD"), timeout=timeout) as r:
        return {"bytes": int(r.headers.get("Content-Length") or 0), "last_modified": r.headers.get("Last-Modified")}


def download(url: str, dest: Path, timeout: int = 300) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(_request(url), timeout=timeout) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(dest)


def extract_zip(zip_path: Path, dest_dir: Path) -> list[str]:
    """Extract a zip into its own folder after checking integrity and member names."""
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f"corrupt zip {zip_path.name}: {bad}")
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        for n in names:
            p = Path(n)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError(f"unsafe member name in {zip_path.name}: {n}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        z.extractall(dest_dir)
    return names


# ------------------------------------------------------------ MSHA pipe files

_SUM = re.compile(r"^SUM\((.*)\)$")


def _clean(b: bytes) -> str:
    return b.strip(b'"').decode("latin-1")


def read_header(path: Path) -> list[str]:
    """Header of an MSHA pipe-delimited file; `SUM(X)` columns are renamed to `X`."""
    with open(path, "rb") as f:
        raw = f.readline().rstrip(b"\r\n").split(b"|")
    return [_SUM.sub(r"\1", _clean(c)) for c in raw]


def find_company_mines(mines_txt: Path, controller_name: str) -> tuple[set[str], set[str], int]:
    """Mines whose current controller is `controller_name`.

    Returns (mine_ids, controller_ids, skipped_rows). Raises if there is no match.
    """
    hdr = read_header(mines_txt)
    ix = {h: i for i, h in enumerate(hdr)}
    i_id, i_cid, i_name = ix["MINE_ID"], ix["CURRENT_CONTROLLER_ID"], ix["CURRENT_CONTROLLER_NAME"]
    mine_ids: set[str] = set()
    ctrl_ids: set[str] = set()
    names: Counter[str] = Counter()
    skipped = 0
    with open(mines_txt, "rb") as f:
        f.readline()
        for line in f:
            p = [_clean(x) for x in line.rstrip(b"\r\n").split(b"|")]
            if len(p) != len(hdr):
                skipped += 1
                continue
            names[p[i_name]] += 1
            if p[i_name] == controller_name:
                mine_ids.add(p[i_id])
                ctrl_ids.add(p[i_cid])
    if not mine_ids:
        token = controller_name.split()[0].lower()
        similar = sorted(n for n in names if token in n.lower())[:10]
        raise ValueError(f"no mines found for controller {controller_name!r}; similar names: {similar}")
    return mine_ids, ctrl_ids, skipped


def filter_table(src: Path, dst: Path, mine_ids: set[str]) -> tuple[int, int]:
    """Copy rows of `src` whose MINE_ID is in `mine_ids` to a UTF-8 (BOM) CSV.

    Returns (rows_written, rows_rejected). Rejected rows have a wrong number of fields.
    """
    hdr = read_header(src)
    n = len(hdr)
    idx = hdr.index("MINE_ID")
    ok = rejected = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f, open(dst, "w", encoding="utf-8-sig", newline="") as out:
        w = csv.writer(out)
        w.writerow(hdr)
        f.readline()
        for line in f:
            head = line.split(b"|", idx + 1)
            if len(head) <= idx or _clean(head[idx]) not in mine_ids:
                continue
            p = [_clean(x) for x in line.rstrip(b"\r\n").split(b"|")]
            if len(p) != n:
                rejected += 1
                continue
            w.writerow(p)
            ok += 1
    return ok, rejected


def csv_to_load_file(src: Path, dst: Path) -> int:
    """Convert a UTF-8 CSV to the file format used for BULK INSERT: UTF-16LE, pipe-delimited, no quotes.

    SQL Server on Linux reads UTF-8 bytes with the wrong code page and has no CODEPAGE option, but it
    reads `widechar` (UTF-16) files correctly. The format cannot quote fields, so a value that contains
    a pipe or a line break is rejected instead of silently breaking the row. Returns the data rows written.
    """
    n = -1  # the header does not count
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, encoding="utf-8-sig", newline="") as f, open(dst, "wb") as out:
        out.write(b"\xff\xfe")
        for row in csv.reader(f):
            for value in row:
                if "|" in value or "\r" in value or "\n" in value:
                    raise ValueError(f"{src.name}: a field contains a pipe or a line break: {value[:40]!r}")
            out.write(("|".join(row) + "\n").encode("utf-16-le"))
            n += 1
    return n


def count_csv_rows(path: Path) -> int:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


# ------------------------------------------------------------ Cochilco Excel

MONTHLY_AGGREGATES = {"Chuqui y R.Tomic", "Total Codelco", "Angloamerican Sur", "Capstone Copper", "TOTAL CHILE"}
ANNUAL_AGGREGATES = {"total codelco", "total chile"}


def _rows(xlsx: Path, sheet: str | None = None) -> list[tuple]:
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    return rows


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _first_row(rows, predicate) -> int:
    for i, r in enumerate(rows):
        if r and r[0] is not None and predicate(str(r[0]).strip().lower()):
            return i
    raise ValueError("header row not found")


def tidy_price_monthly(xlsx: Path) -> list[dict]:
    rows = _rows(xlsx)
    start = _first_row(rows, lambda s: s.startswith("mes"))
    out = []
    for r in rows[start + 1 :]:
        if isinstance(r[0], dt.datetime):
            out.append({"month": r[0].date().isoformat(), "bml_cusd_lb": _num(r[1]), "comex_cusd_lb": _num(r[2])})
    return out


def tidy_price_annual(xlsx: Path) -> list[dict]:
    rows = _rows(xlsx)
    start = _first_row(rows, lambda s: s.startswith("año"))
    out = []
    for r in rows[start + 1 :]:
        if isinstance(r[0], int) and not isinstance(r[0], bool):
            out.append({"year": r[0], "bml_cusd_lb": _num(r[1]), "comex_cusd_lb": _num(r[2])})
    return out


def tidy_production_monthly(xlsx: Path) -> list[dict]:
    """Long format: one row per month and mine/company column (thousand metric tons of fine copper).

    Months without a positive TOTAL CHILE are placeholders and are dropped.
    """
    rows = _rows(xlsx)
    start = _first_row(rows, lambda s: s.startswith("mes"))
    header = [str(c).strip() if c is not None else None for c in rows[start]]
    total_col = header.index("TOTAL CHILE")
    out = []
    for r in rows[start + 1 :]:
        if not isinstance(r[0], dt.datetime):
            continue
        total = _num(r[total_col])
        if not total or total <= 0:
            continue
        for i, name in enumerate(header):
            if i == 0 or not name:
                continue
            v = _num(r[i])
            if v is not None:
                out.append(
                    {
                        "month": r[0].date().isoformat(),
                        "faena": name,
                        "is_aggregate": int(name in MONTHLY_AGGREGATES),
                        "kt_fine_cu": v,
                    }
                )
    return out


def tidy_production_annual(xlsx: Path) -> list[dict]:
    rows = _rows(xlsx, "Hoja1")
    years = {i: int(y) for i, y in enumerate(rows[0]) if isinstance(y, int) and not isinstance(y, bool)}
    out = []
    for r in rows[1:]:
        name, unit = r[0], r[1]
        if not name or unit != "Miles TM":
            continue
        clean = re.sub(r"\s*\(\d+\)\s*$", "", str(name)).strip()
        for i, year in years.items():
            v = _num(r[i]) if i < len(r) else None
            if v is not None:
                out.append(
                    {
                        "year": year,
                        "faena": clean,
                        "is_aggregate": int(clean.lower() in ANNUAL_AGGREGATES),
                        "kt_fine_cu": v,
                    }
                )
    return out


def write_csv(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)
    return len(rows)
