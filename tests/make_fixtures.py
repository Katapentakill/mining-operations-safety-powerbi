"""Build the small CI fixture set from the real filtered CSVs (run by hand, output is committed).

Usage: python tests/make_fixtures.py
Picks a few mines and keeps a capped sample of their rows, always including edge cases:
fatalities, unknown codes, unknown accident time, contractor accidents, other controllers,
violations without controller or without penalty, and a non-ASCII narrative.
Workforce tables keep every row of the chosen mines so quarterly and yearly hours still reconcile.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import common  # noqa: E402

SRC = common.data_dir(common.load_config()) / "csv"
DST = ROOT / "tests" / "fixtures" / "csv"
SLUG = common.load_config()["company"]["slug"]


def read(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames), list(r)


def write(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} filas")


def spaced(rows: list[dict], n: int) -> list[dict]:
    """n rows evenly spaced through rows (all of them if fewer)."""
    if len(rows) <= n:
        return list(rows)
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def pick(rows: list[dict], predicate, limit: int) -> list[dict]:
    return [r for r in rows if predicate(r)][:limit]


def unique(rows: list[dict], key: str) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        if r[key] not in seen:
            seen.add(r[key])
            out.append(r)
    return out


def main() -> int:
    h_m, mines = read(SRC / SLUG / "mines.csv")
    h_a, acc = read(SRC / SLUG / "accidents.csv")
    h_v, vio = read(SRC / SLUG / "violations.csv")
    h_s, ass = read(SRC / SLUG / "assessed_violations.csv")
    h_i, ins = read(SRC / SLUG / "inspections.csv")
    h_y, yearly = read(SRC / SLUG / "mines_prod_yearly.csv")
    h_q, quarterly = read(SRC / SLUG / "mines_prod_quarterly.csv")
    h_c, hist = read(SRC / SLUG / "controller_operator_history.csv")

    n_acc, n_vio = Counter(r["MINE_ID"] for r in acc), Counter(r["MINE_ID"] for r in vio)
    n_work = Counter(r["MINE_ID"] for r in quarterly)
    cand = [
        m for m in mines
        if 8 <= n_acc[m["MINE_ID"]] <= 90 and n_vio[m["MINE_ID"]] >= 5 and n_work[m["MINE_ID"]] > 0
    ]
    cand.sort(key=lambda m: m["MINE_ID"])
    chosen: list[dict] = []
    for want in (
        lambda m: m["CURRENT_MINE_STATUS"] == "Active" and m["LATITUDE"],
        lambda m: m["CURRENT_MINE_STATUS"] != "Active" and m["LATITUDE"],
        lambda m: not m["LATITUDE"],
        lambda m: True,
    ):
        for m in cand:
            if m not in chosen and want(m):
                chosen.append(m)
                break
    ids = {m["MINE_ID"] for m in chosen}
    print("minas elegidas:", sorted(ids))

    a = [r for r in acc if r["MINE_ID"] in ids]
    edge_a = (
        pick(a, lambda r: r["DEGREE_INJURY_CD"] in ("01", "?"), 6)
        + pick(a, lambda r: r["ACCIDENT_TIME"] == "9999", 3)
        + pick(a, lambda r: r["CONTRACTOR_ID"] != "", 4)
        + pick(a, lambda r: r["CONTROLLER_ID"] != "0067299", 4)
        + pick(a, lambda r: any(ord(ch) > 127 for ch in r["NARRATIVE"]), 2)
    )
    acc_out = unique(edge_a + spaced(a, 60), "DOCUMENT_NO")

    v = [r for r in vio if r["MINE_ID"] in ids]
    assessed_pairs = {(r["EVENT_NBR"], r["VIOLATION_NO"]) for r in ass}
    edge_v = (
        pick(v, lambda r: r["CONTROLLER_ID"] == "", 5)
        + pick(v, lambda r: (r["EVENT_NO"], r["VIOLATION_NO"]) not in assessed_pairs, 5)
        + pick(v, lambda r: r["SIG_SUB"] == "", 2)
    )
    vio_out = unique(edge_v + spaced(v, 80), "VIOLATION_NO")
    keep_pairs = {(r["EVENT_NO"], r["VIOLATION_NO"]) for r in vio_out}
    ass_out = [r for r in ass if (r["EVENT_NBR"], r["VIOLATION_NO"]) in keep_pairs]

    ins_out = spaced([r for r in ins if r["MINE_ID"] in ids], 40)
    yearly_out = [r for r in yearly if r["MINE_ID"] in ids]
    quarterly_out = [r for r in quarterly if r["MINE_ID"] in ids]
    hist_out = [r for r in hist if r["MINE_ID"] in ids]

    fx = DST / "fixture"
    write(fx / "mines.csv", h_m, chosen)
    write(fx / "accidents.csv", h_a, acc_out)
    write(fx / "violations.csv", h_v, vio_out)
    write(fx / "assessed_violations.csv", h_s, ass_out)
    write(fx / "inspections.csv", h_i, ins_out)
    write(fx / "mines_prod_yearly.csv", h_y, yearly_out)
    write(fx / "mines_prod_quarterly.csv", h_q, quarterly_out)
    write(fx / "controller_operator_history.csv", h_c, hist_out)

    ctx = DST / "chile_context"
    h_p, price = read(SRC / "chile_context" / "cu_price_monthly.csv")
    write(ctx / "cu_price_monthly.csv", h_p, [r for r in price if "1999-12-01" <= r["month"] <= "2000-02-01" or r["month"] >= "2023-01-01"])
    h_k, prod = read(SRC / "chile_context" / "cu_production_monthly.csv")
    write(ctx / "cu_production_monthly.csv", h_k, [r for r in prod if "2024-01-01" <= r["month"] <= "2024-03-01"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
