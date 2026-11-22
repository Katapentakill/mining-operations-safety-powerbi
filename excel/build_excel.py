"""Build the base workbook (MiningSafety_Excel_base.xlsx): a formula-driven dashboard with native Excel charts over the aggregated MSHA figures.

    python excel/build_excel.py                       # needs the SQL Server container (docker compose up -d --wait)
    python excel/build_excel.py --anio 2024 --mina "Freeport-McMoRan Morenci Inc."   # open with a selection

The workbook carries aggregates only (no raw MSHA rows). Every number on the dashboard is a live formula over the tables in the
`Datos` sheet, so changing the year or mine drop-downs recalculates the cards and the charts. The cached results written next to
each formula are computed here with pandas, so viewers that do not recalculate still show the right numbers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

if not sys.flags.utf8_mode and __name__ == "__main__":  # docker/sqlcmd output and accents: force UTF-8 on Windows
    os.execv(sys.executable, [sys.executable, "-X", "utf8", *sys.argv])

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Palette of the Power BI report (powerbi/.../CopperMining.json)
COPPER, BLUE, GREEN, PURPLE, SAND, RED, GRAY = "#B8602A", "#4F6D8F", "#3E8E85", "#7A5C8E", "#D9B382", "#C0392B", "#A7ADB3"
INK, MUTED, PALE, BG, LINE = "#2B2F33", "#6B7077", "#F3E6D5", "#FBF8F4", "#E4DCD2"
GROUP_COLORS = [RED, COPPER, BLUE, GRAY]  # fatality, lost days, no lost days, other

OUT_DEFAULT = HERE / "MiningSafety_Excel_base.xlsx"  # the published workbook is this file plus the PivotTables added in Excel (see PASOS_MANUALES.md)
MIN_HORAS_TASA = 50_000  # the per-mine rate is shown only with at least this many hours (one isolated case would distort it)


# ---------------------------------------------------------------- cached values (pandas mirror of the formulas)
class Sel:
    def __init__(self, anio, mina):
        self.anio = anio
        self.mina = mina
        self.todos = str(anio) == "Todos"
        self.ymin = 0 if self.todos else int(anio)
        self.ymax = 9999 if self.todos else int(anio)
        self.crit = "*" if mina == "Todas" else mina


def _rows(a: pd.DataFrame, ymin: int, ymax: int, mina: str | None) -> pd.DataFrame:
    m = (a["anio"] >= ymin) & (a["anio"] <= ymax)
    if mina and mina != "*":
        m &= a["mina"] == mina
    return a[m]


def _rate(sub: pd.DataFrame):
    h = sub["horas"].sum()
    return sub["casos_tasa"].sum() * 200000 / h if h else None


def _pct_text(cur, prev):
    if not prev:
        return ""
    x = cur / prev - 1
    return ("+" if x >= 0 else "") + str(round(x * 100)) + "%"


def build_workbook(frames: dict[str, pd.DataFrame], out: Path, anio="Todos", mina="Todas", snapshot: str | None = None) -> dict:
    a = frames["anio_mina"].copy()
    g = frames["gravedad"].copy()
    minas = frames["minas"].copy()
    # text columns that make the table handy for PivotTables and slicers (decade, state and status of the mine)
    a["decada"] = (a["anio"] // 10 * 10).astype(str) + "s"
    a = a.merge(minas[["mina", "estado", "situacion"]], on="mina", how="left")
    sel = Sel(anio, mina)
    years = list(range(int(a["anio"].min()), int(a["anio"].max()) + 1))
    groups = list(g.sort_values("orden").drop_duplicates("grupo")["grupo"])
    snapshot = snapshot or dt.date.today().isoformat()

    # mines ordered by total accidents (descending): the Minas sheet and the sparkline matrix use this order
    tot = a.groupby("mina")["accidentes"].sum()
    minas["total"] = minas["mina"].map(tot).fillna(0)
    minas = minas.sort_values(["total", "mina"], ascending=[False, True]).reset_index(drop=True)
    n_min = len(minas)

    wb = xlsxwriter.Workbook(str(out), {"default_format_properties": {"font_name": "Calibri", "font_size": 10, "font_color": INK},
                                        "use_future_functions": True})
    wb.set_properties({"title": "Seguridad minera (MSHA): panel en Excel", "author": "Alexander Tapia Olmedo",
                       "comments": "Cifras agregadas de datos publicos de MSHA. Proyecto independiente."})

    def F(**kw):
        return wb.add_format(kw)

    f_title = F(bold=True, font_size=22, font_color=INK, valign="vcenter")
    f_sub = F(font_size=10, font_color=MUTED, valign="vcenter")
    f_h2 = F(bold=True, font_size=13, font_color=COPPER)
    f_txt = F(text_wrap=True, valign="top")
    f_bold = F(bold=True)
    f_head = F(bold=True, font_color="#FFFFFF", bg_color=COPPER, valign="vcenter", border=1, border_color=COPPER)
    f_cell = F(border=1, border_color=LINE, valign="vcenter")
    f_int = F(num_format="#,##0", border=1, border_color=LINE, valign="vcenter")
    f_dec = F(num_format="0.00", border=1, border_color=LINE, valign="vcenter")
    f_link = F(font_color=COPPER, underline=1, bold=True)
    f_small = F(font_size=9, font_color=MUTED, text_wrap=True, valign="top")

    # ------------------------------------------------------------ sheets (order of the tabs)
    ws_ini = wb.add_worksheet("Inicio")
    ws_pan = wb.add_worksheet("Panel")
    ws_min = wb.add_worksheet("Minas")
    ws_dat = wb.add_worksheet("Datos")
    ws_piv = wb.add_worksheet("Pivote")
    ws_how = wb.add_worksheet("Cómo está hecho")
    ws_cal = wb.add_worksheet("Calc")
    for w in (ws_ini, ws_pan, ws_min, ws_dat, ws_piv, ws_how, ws_cal):
        w.hide_gridlines(2)
    ws_pan.set_tab_color(COPPER)
    ws_cal.set_tab_color(GRAY)

    # ------------------------------------------------------------ Datos: three Excel tables
    ws_dat.write("A1", "Datos agregados (fuente: MSHA, vistas rpt del proyecto)", f_h2)
    ws_dat.write("A2", "Una fila por mina y año; sin filas crudas. Las tablas tienen nombre y alimentan todas las fórmulas.", f_sub)
    cols_a = [("mina", "Mina", f_cell), ("anio", "Año", f_cell), ("accidentes", "Accidentes", f_int), ("fatalidades", "Fatalidades", f_int),
              ("casos_tasa", "Casos tasa", f_int), ("dias_perdidos", "Días perdidos", f_int), ("infracciones", "Infracciones", f_int),
              ("multa_pagada", "Multa pagada", f_int), ("horas", "Horas", f_int),
              ("decada", "Década", f_cell), ("estado", "Estado", f_cell), ("situacion", "Situación", f_cell)]
    ws_dat.add_table(2, 0, 2 + len(a), len(cols_a) - 1, {
        "name": "t_anio_mina", "style": "Table Style Light 1", "data": a[[c[0] for c in cols_a]].values.tolist(),
        "columns": [{"header": c[1], "header_format": f_head, "format": c[2]} for c in cols_a]})
    cols_g = [("mina", "Mina", f_cell), ("anio", "Año", f_cell), ("grupo", "Grupo", f_cell), ("accidentes", "Accidentes", f_int)]
    ws_dat.add_table(2, 13, 2 + len(g), 13 + len(cols_g) - 1, {
        "name": "t_gravedad", "style": "Table Style Light 1", "data": g[[c[0] for c in cols_g]].values.tolist(),
        "columns": [{"header": c[1], "header_format": f_head, "format": c[2]} for c in cols_g]})
    cols_m = [("mina", "Mina", f_cell), ("estado", "Estado", f_cell), ("situacion", "Situación", f_cell), ("tipo", "Tipo", f_cell),
              ("empleados", "Empleados", f_int)]
    ws_dat.add_table(2, 18, 2 + len(minas), 18 + len(cols_m) - 1, {
        "name": "t_minas", "style": "Table Style Light 1", "data": minas[[c[0] for c in cols_m]].values.tolist(),
        "columns": [{"header": c[1], "header_format": f_head, "format": c[2]} for c in cols_m]})
    for col, w in {0: 34, 1: 7, 2: 11, 3: 11, 4: 11, 5: 13, 6: 12, 7: 13, 8: 14, 9: 9, 10: 14, 11: 13, 12: 3, 13: 34, 14: 7, 15: 20, 16: 11,
                   17: 3, 18: 34, 19: 14, 20: 13, 21: 14, 22: 11}.items():
        ws_dat.set_column(col, col, w)
    ws_dat.freeze_panes(3, 0)

    # ------------------------------------------------------------ Calc: selectors, yearly series, mine matrix, lists
    wb.define_name("selAnio", "=Panel!$D$4")
    wb.define_name("selMina", "=Panel!$H$4")
    wb.define_name("yMin", "=Calc!$B$3")
    wb.define_name("yMax", "=Calc!$B$4")
    wb.define_name("critMina", "=Calc!$B$5")
    ws_cal.write("A1", "Hoja auxiliar: valores intermedios que alimentan el panel y los gráficos (no editar).", f_h2)
    ws_cal.write("A3", "Año desde"); ws_cal.write_formula("B3", '=IF(selAnio="Todos",0,selAnio)', None, sel.ymin)
    ws_cal.write("A4", "Año hasta"); ws_cal.write_formula("B4", '=IF(selAnio="Todos",9999,selAnio)', None, sel.ymax)
    ws_cal.write("A5", "Criterio mina"); ws_cal.write_formula("B5", '=IF(selMina="Todas","*",selMina)', None, sel.crit)

    def sf(col, year_expr=None, mina_expr="critMina", table="t_anio_mina", ycol="Año", mcol="Mina"):
        yc = (f'{table}[{ycol}],{year_expr}' if year_expr else f'{table}[{ycol}],">="&yMin,{table}[{ycol}],"<="&yMax')
        return f"SUMIFS({table}[{col}],{yc},{table}[{mcol}],{mina_expr})"

    # yearly series (rows 8..): respects the mine selector
    hdr = ["Año", "Accidentes", "Otros años", "Año elegido", "Tasa", "Infracciones", "Multa (M US$)"]
    for j, h in enumerate(hdr):
        ws_cal.write(6, j, h, f_head)
    cal_y0 = 7  # zero-based first data row (Excel row 8)
    for i, y in enumerate(years):
        r = cal_y0 + i
        xr = r + 1
        sub = _rows(a, y, y, None if sel.crit == "*" else sel.crit)
        acc = int(sub["accidentes"].sum())
        rate = _rate(sub)
        ws_cal.write_number(r, 0, y)
        ws_cal.write_formula(r, 1, f"={sf('Accidentes', f'A{xr}')}", None, acc)
        is_sel = (not sel.todos) and y == sel.ymin
        ws_cal.write_formula(r, 2, f'=IF(OR(selAnio="Todos",A{xr}<>selAnio),B{xr},NA())', None, "#N/A" if is_sel else acc)
        ws_cal.write_formula(r, 3, f'=IF(AND(selAnio<>"Todos",A{xr}=selAnio),B{xr},NA())', None, acc if is_sel else "#N/A")
        ws_cal.write_formula(r, 4, f"=IFERROR({sf('Casos tasa', f'A{xr}')}*200000/{sf('Horas', f'A{xr}')},NA())", None,
                             round(rate, 6) if rate is not None else "#N/A")
        ws_cal.write_formula(r, 5, f"={sf('Infracciones', f'A{xr}')}", None, int(sub["infracciones"].sum()))
        ws_cal.write_formula(r, 6, f"={sf('Multa pagada', f'A{xr}')}/1000000", None, float(sub["multa_pagada"].sum()) / 1e6)
    y_first, y_last = cal_y0 + 1, cal_y0 + len(years)  # Excel row numbers

    # mine matrix (rows 41..): accidents per mine and year; same order as the Minas sheet
    mrow0 = 40  # zero-based first matrix data row (Excel row 41)
    ws_cal.write(mrow0 - 1, 0, "Mina", f_head)
    for j, y in enumerate(years):
        ws_cal.write_number(mrow0 - 1, 1 + j, y, f_head)
    c_tot, c_sel, c_tb = 1 + len(years), 2 + len(years), 3 + len(years)
    ws_cal.write(mrow0 - 1, c_tot, "Total", f_head)
    ws_cal.write(mrow0 - 1, c_sel, "Año elegido", f_head)
    ws_cal.write(mrow0 - 1, c_tb, "Orden", f_head)
    ranks = []
    for i, row in minas.iterrows():
        r = mrow0 + i
        xr = r + 1
        ws_cal.write_formula(r, 0, f"=Minas!B{6 + i}", None, row["mina"])
        for j, y in enumerate(years):
            v = int(_rows(a, y, y, row["mina"])["accidentes"].sum())
            ws_cal.write_formula(r, 1 + j, f"={sf('Accidentes', f'{xl_col_to_name(1 + j)}${mrow0}', f'$A{xr}')}", None, v)
        first, last = xl_col_to_name(1), xl_col_to_name(len(years))
        ws_cal.write_formula(r, c_tot, f"=SUM({first}{xr}:{last}{xr})", None, int(_rows(a, 0, 9999, row["mina"])["accidentes"].sum()))
        v_sel = int(_rows(a, sel.ymin, sel.ymax, row["mina"])["accidentes"].sum())
        ws_cal.write_formula(r, c_sel, f"={sf('Accidentes', None, f'$A{xr}')}", None, v_sel)
        tb = v_sel + xr / 1_000_000
        ranks.append((tb, row["mina"], v_sel))
        ws_cal.write_formula(r, c_tb, f"={xl_col_to_name(c_sel)}{xr}+ROW()/1000000", None, tb)
    m_first, m_last = mrow0 + 1, mrow0 + n_min
    rng_tb = f"${xl_col_to_name(c_tb)}${m_first}:${xl_col_to_name(c_tb)}${m_last}"
    rng_nm = f"$A${m_first}:$A${m_last}"
    rng_sel = f"${xl_col_to_name(c_sel)}${m_first}:${xl_col_to_name(c_sel)}${m_last}"

    # Top 5 block (I7:L12)
    for j, h in enumerate(["Puesto", "Orden", "Mina", "Accidentes"]):
        ws_cal.write(6, 8 + j, h, f_head)
    n_top = min(5, n_min)
    top = sorted(ranks, reverse=True)[:n_top]
    for k in range(n_top):
        r = 7 + k
        xr = r + 1
        ws_cal.write_number(r, 8, k + 1)
        ws_cal.write_formula(r, 9, f"=LARGE({rng_tb},I{xr})", None, top[k][0])
        ws_cal.write_formula(r, 10, f"=INDEX({rng_nm},MATCH(J{xr},{rng_tb},0))", None, top[k][1])
        ws_cal.write_formula(r, 11, f"=INDEX({rng_sel},MATCH(J{xr},{rng_tb},0))", None, top[k][2])

    # severity block (N7:O11) respects both selectors
    ws_cal.write(6, 13, "Grupo", f_head)
    ws_cal.write(6, 14, "Accidentes", f_head)
    for k, grp in enumerate(groups):
        r = 7 + k
        sub = g[(g["grupo"] == grp) & (g["anio"] >= sel.ymin) & (g["anio"] <= sel.ymax)]
        if sel.crit != "*":
            sub = sub[sub["mina"] == sel.crit]
        ws_cal.write(r, 13, grp)
        ws_cal.write_formula(r, 15, f'=N{r + 1}&" ("&O{r + 1}&")"', None, f"{grp} ({int(sub['accidentes'].sum())})")
        ws_cal.write_formula(
            r, 14,
            f'=SUMIFS(t_gravedad[Accidentes],t_gravedad[Grupo],N{r + 1},t_gravedad[Año],">="&yMin,t_gravedad[Año],"<="&yMax,t_gravedad[Mina],critMina)',
            None, int(sub["accidentes"].sum()))

    # chart titles that follow the selection
    ws_cal.write("Q7", "Títulos", f_head)
    t_year = "todos los años" if sel.todos else str(sel.anio)
    t_mine = "las 43 minas" if sel.mina == "Todas" else sel.mina
    ws_cal.write_formula("Q8", '="Accidentes por año · "&IF(selMina="Todas","las 43 minas",selMina)', None, f"Accidentes por año · {t_mine}")
    ws_cal.write_formula("Q9", '="Infracciones y multa pagada por año · "&IF(selMina="Todas","las 43 minas",selMina)', None,
                         f"Infracciones y multa pagada por año · {t_mine}")
    ws_cal.write_formula("Q10", '="Las 5 minas con más accidentes · "&IF(selAnio="Todos","todos los años",selAnio)', None,
                         f"Las 5 minas con más accidentes · {t_year}")
    ws_cal.write_formula("Q11", '="Gravedad de las lesiones · "&IF(selAnio="Todos","todos los años",selAnio)&" · "&IF(selMina="Todas","las 43 minas",selMina)',
                         None, f"Gravedad de las lesiones · {t_year} · {t_mine}")

    # lists for the drop-downs (AH, AI)
    ws_cal.write("AH7", "Años", f_head); ws_cal.write("AI7", "Minas", f_head)
    year_list = ["Todos"] + years
    for i, v in enumerate(year_list):
        ws_cal.write(7 + i, 33, v)
    mine_list = ["Todas"] + sorted(minas["mina"])
    for i, v in enumerate(mine_list):
        ws_cal.write(7 + i, 34, v)
    ws_cal.set_column(0, 0, 34); ws_cal.set_column(1, 28, 9); ws_cal.set_column(10, 10, 34); ws_cal.set_column(13, 13, 20)
    ws_cal.set_column(15, 15, 30); ws_cal.set_column(16, 16, 60); ws_cal.set_column(34, 34, 34)

    # ------------------------------------------------------------ Panel
    ws_pan.set_column("A:A", 2)
    ws_pan.set_column("B:M", 14)
    ws_pan.set_column("N:N", 2)
    ws_pan.set_row(0, 38)
    ws_pan.merge_range("B1:M1", "Seguridad minera · Panel de control", f_title)
    ws_pan.merge_range("B2:M2", "Accidentes, infracciones y horas de las 43 minas de Freeport-McMoRan (EE. UU.) · datos públicos de MSHA, 2000 a 2026", f_sub)

    f_lab = F(bold=True, font_color=MUTED, align="right", valign="vcenter")
    f_selbox = F(bold=True, font_size=12, font_color=INK, bg_color="#FFFFFF", border=2, border_color=COPPER, align="center", valign="vcenter")
    ws_pan.write("B4", "", None)
    ws_pan.merge_range("B4:C4", "Año", f_lab)
    ws_pan.merge_range("D4:E4", sel.anio if sel.todos else int(sel.anio), f_selbox)
    ws_pan.merge_range("F4:G4", "Mina", f_lab)
    ws_pan.merge_range("H4:L4", sel.mina, f_selbox)
    ws_pan.set_row(3, 24)
    ws_pan.data_validation("D4", {"validate": "list", "source": f"=Calc!$AH$8:$AH${7 + len(year_list)}",
                                  "input_title": "Año", "input_message": "Elige un año o «Todos».",
                                  "error_title": "Valor no válido", "error_message": "Elige un año de la lista."})
    ws_pan.data_validation("H4", {"validate": "list", "source": f"=Calc!$AI$8:$AI${7 + len(mine_list)}",
                                  "input_title": "Mina", "input_message": "Elige una mina o «Todas».",
                                  "error_title": "Valor no válido", "error_message": "Elige una mina de la lista."})
    f_info = F(font_color=MUTED, italic=True, valign="vcenter")
    info_v = ("43 minas" if sel.mina == "Todas" else
              f'{sel.mina} · {minas.loc[minas.mina == sel.mina, "estado"].iloc[0]} · {minas.loc[minas.mina == sel.mina, "situacion"].iloc[0]}')
    info_v += " · todos los años" if sel.todos else f" · {sel.anio}"
    ws_pan.merge_range("B5:M5", "", f_info)
    ws_pan.write_formula("B5", '=IF(selMina="Todas","43 minas",selMina&" · "&XLOOKUP(selMina,t_minas[Mina],t_minas[Estado],"")&" · "&'
                               'XLOOKUP(selMina,t_minas[Mina],t_minas[Situación],""))&IF(selAnio="Todos"," · todos los años"," · "&selAnio)',
                         f_info, info_v)

    cur = _rows(a, sel.ymin, sel.ymax, None if sel.crit == "*" else sel.crit)
    prv = _rows(a, sel.ymin - 1, sel.ymin - 1, None if sel.crit == "*" else sel.crit) if not sel.todos else a.iloc[0:0]
    prev_f = lambda col: sf(col, "selAnio-1")
    cards = [
        ("ACCIDENTES", COPPER, f"={sf('Accidentes')}", int(cur["accidentes"].sum()), "#,##0",
         f'=IF(selAnio="Todos","reportados a MSHA",IFERROR(IF(ROUND(({sf("Accidentes")})/({prev_f("Accidentes")})*100-100,0)>=0,"+","")&ROUND(({sf("Accidentes")})/({prev_f("Accidentes")})*100-100,0)&"% vs "&(selAnio-1),""))',
         "reportados a MSHA" if sel.todos else (_pct_text(int(cur["accidentes"].sum()), int(prv["accidentes"].sum())) + f" vs {int(sel.ymin) - 1}"
                                                if int(prv["accidentes"].sum()) else "")),
        ("FATALIDADES", RED, f"={sf('Fatalidades')}", int(cur["fatalidades"].sum()), "#,##0", None, "casos con resultado de muerte"),
        ("INFRACCIONES", BLUE, f"={sf('Infracciones')}", int(cur["infracciones"].sum()), "#,##0", None, "citadas por inspectores"),
        ("MULTA PAGADA (US$)", GREEN, f"={sf('Multa pagada')}", float(cur["multa_pagada"].sum()), "#,##0", None, "multas efectivamente pagadas"),
        ("HORAS TRABAJADAS", PURPLE, f"={sf('Horas')}", int(cur["horas"].sum()), '0.0,," M"', None, "horas con datos de MSHA"),
        ("TASA DE INCIDENCIA", COPPER, f'=IFERROR({sf("Casos tasa")}*200000/{sf("Horas")},"s/d")',
         round(_rate(cur), 6) if _rate(cur) is not None else "s/d", "0.00",
         f'=IF(selAnio="Todos","casos por 200.000 horas",IFERROR("vs "&(selAnio-1)&": "&ROUND({prev_f("Casos tasa")}*200000/{prev_f("Horas")},1),"casos por 200.000 horas"))',
         "casos por 200.000 horas" if sel.todos else (f"vs {int(sel.ymin) - 1}: {round(_rate(prv), 1)}".replace(".", ",") if _rate(prv) else "casos por 200.000 horas")),
    ]
    for k, (label, color, fml, val, numfmt, dfml, dval) in enumerate(cards):
        c0 = 1 + 2 * k
        c1 = c0 + 1
        lab = F(bold=True, font_size=9, font_color=MUTED, bg_color="#FFFFFF", top=5, top_color=color, left=1, right=1, left_color=LINE,
                right_color=LINE, align="left", valign="vcenter", indent=1)
        valf = F(bold=True, font_size=22, font_color=color, bg_color="#FFFFFF", left=1, right=1, left_color=LINE, right_color=LINE,
                 align="left", valign="vcenter", num_format=numfmt, indent=1)
        dl = F(font_size=9, font_color=MUTED, bg_color="#FFFFFF", left=1, right=1, bottom=1, left_color=LINE, right_color=LINE,
               bottom_color=LINE, align="left", valign="vcenter", indent=1)
        ws_pan.merge_range(6, c0, 6, c1, label, lab)
        ws_pan.merge_range(7, c0, 8, c1, "", valf)
        ws_pan.write_formula(7, c0, fml, valf, val)
        ws_pan.merge_range(9, c0, 9, c1, "", dl)
        if dfml:
            ws_pan.write_formula(9, c0, dfml, dl, dval)
        else:
            ws_pan.write(9, c0, dval, dl)
    ws_pan.set_row(6, 18)
    ws_pan.set_row(9, 18)

    # charts
    def style_axis(ch):
        ch.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
        ch.set_plotarea({"fill": {"none": True}})
        ch.set_legend({"position": "bottom", "font": {"size": 9, "color": INK}})

    calc = "Calc"
    cats = f"={calc}!$A${y_first}:$A${y_last}"
    # 1) accidents by year (columns, selected year highlighted) + incidence rate (line, secondary axis)
    ch1 = wb.add_chart({"type": "column"})
    ch1.add_series({"name": "Accidentes", "categories": cats, "values": f"={calc}!$C${y_first}:$C${y_last}", "fill": {"color": COPPER},
                    "gap": 40, "overlap": 100})
    ch1.add_series({"name": "Año elegido", "categories": cats, "values": f"={calc}!$D${y_first}:$D${y_last}", "fill": {"color": INK}})
    ln1 = wb.add_chart({"type": "line"})
    ln1.add_series({"name": "Tasa por 200.000 h", "categories": cats, "values": f"={calc}!$E${y_first}:$E${y_last}", "y2_axis": True,
                    "line": {"color": BLUE, "width": 2.25}, "marker": {"type": "circle", "size": 4, "fill": {"color": BLUE}, "border": {"color": BLUE}}})
    ch1.combine(ln1)
    ch1.set_title({"name": f"={calc}!$Q$8", "name_font": {"size": 12, "bold": True, "color": INK}, "overlay": False})
    ch1.set_x_axis({"num_font": {"size": 8, "rotation": -45}, "line": {"color": LINE}, "interval_unit": 2})
    ch1.set_y_axis({"num_font": {"size": 9}, "major_gridlines": {"visible": True, "line": {"color": LINE, "width": 0.5}}, "line": {"none": True}})
    ln1.set_y2_axis({"num_font": {"size": 9, "color": BLUE}, "line": {"none": True}, "num_format": "0.0"})
    style_axis(ch1)
    ch1.set_size({"width": 612, "height": 300})
    ws_pan.insert_chart("B12", ch1, {"x_offset": 0, "y_offset": 4})

    # 2) violations (columns) and paid penalty (line, secondary axis, millions of US$)
    ch2 = wb.add_chart({"type": "column"})
    ch2.add_series({"name": "Infracciones", "categories": cats, "values": f"={calc}!$F${y_first}:$F${y_last}", "fill": {"color": BLUE}, "gap": 40})
    ln2 = wb.add_chart({"type": "line"})
    ln2.add_series({"name": "Multa pagada (M US$)", "categories": cats, "values": f"={calc}!$G${y_first}:$G${y_last}", "y2_axis": True,
                    "line": {"color": COPPER, "width": 2.25}, "marker": {"type": "circle", "size": 4, "fill": {"color": COPPER}, "border": {"color": COPPER}}})
    ch2.combine(ln2)
    ch2.set_title({"name": f"={calc}!$Q$9", "name_font": {"size": 12, "bold": True, "color": INK}, "overlay": False})
    ch2.set_x_axis({"num_font": {"size": 8, "rotation": -45}, "line": {"color": LINE}, "interval_unit": 2})
    ch2.set_y_axis({"num_font": {"size": 9}, "major_gridlines": {"visible": True, "line": {"color": LINE, "width": 0.5}}, "line": {"none": True}})
    ln2.set_y2_axis({"num_font": {"size": 9, "color": COPPER}, "line": {"none": True}, "num_format": "0.0"})
    style_axis(ch2)
    ch2.set_size({"width": 612, "height": 300})
    ws_pan.insert_chart("H12", ch2, {"x_offset": 0, "y_offset": 4})

    # 3) top 5 mines (horizontal bars)
    ch3 = wb.add_chart({"type": "bar"})
    ch3.add_series({"name": "Accidentes", "categories": f"={calc}!$K$8:$K${7 + n_top}", "values": f"={calc}!$L$8:$L${7 + n_top}", "fill": {"color": COPPER}, "gap": 50,
                    "data_labels": {"value": True, "num_format": "#,##0", "font": {"size": 9, "color": INK}}})
    ch3.set_title({"name": f"={calc}!$Q$10", "name_font": {"size": 12, "bold": True, "color": INK}, "overlay": False})
    ch3.set_y_axis({"reverse": True, "num_font": {"size": 9}, "line": {"color": LINE}})
    ch3.set_x_axis({"visible": False, "major_gridlines": {"visible": False}})
    style_axis(ch3)
    ch3.set_legend({"none": True})
    ch3.set_size({"width": 612, "height": 300})
    ws_pan.insert_chart("B28", ch3, {"x_offset": 0, "y_offset": 4})

    # 4) severity (doughnut)
    ch4 = wb.add_chart({"type": "doughnut"})
    ch4.add_series({"name": "Gravedad", "categories": f"={calc}!$P$8:$P${7 + len(groups)}", "values": f"={calc}!$O$8:$O${7 + len(groups)}",
                    "points": [{"fill": {"color": c}} for c in GROUP_COLORS[:len(groups)]],
                    "data_labels": {"percentage": True, "font": {"size": 9, "color": "#FFFFFF", "bold": True},
                                    "custom": [{"delete": True}] + [None] * (len(groups) - 1)}})
    ch4.set_title({"name": f"={calc}!$Q$11", "name_font": {"size": 12, "bold": True, "color": INK}, "overlay": False})
    ch4.set_hole_size(55)
    style_axis(ch4)
    ch4.set_legend({"position": "right", "font": {"size": 9, "color": INK}})
    ch4.set_size({"width": 612, "height": 300})
    ws_pan.insert_chart("H28", ch4, {"x_offset": 0, "y_offset": 4})

    f_foot = F(font_size=9, font_color=MUTED, text_wrap=True, valign="top")
    ws_pan.merge_range("B44:M45", "Fuente: MSHA (Mine Safety and Health Administration, EE. UU.), datos abiertos; foto del "
                                  f"{snapshot}. Tasa de incidencia = casos de lesión del personal propio × 200.000 / horas trabajadas, solo en trimestres con horas. "
                                  "Proyecto independiente, sin afiliación con MSHA ni Freeport-McMoRan.", f_foot)
    ws_pan.set_landscape()
    ws_pan.set_paper(9)
    ws_pan.fit_to_pages(1, 1)
    ws_pan.print_area("A1:N45")
    ws_pan.set_default_row(18)

    # ------------------------------------------------------------ Minas
    ws_min.set_column("A:A", 2)
    ws_min.set_column("B:B", 36)
    ws_min.set_column("C:E", 14)
    ws_min.set_column("F:I", 14)
    ws_min.set_column("J:J", 28)
    ws_min.write("B1", "Minas", f_title)
    ws_min.write("B2", "Una fila por mina, ordenadas por accidentes; las cifras son fórmulas sobre la tabla t_anio_mina y la tendencia es un minigráfico por año. "
                       "La tasa se muestra solo con 50.000 horas o más (con menos, un caso aislado la dispara).", f_sub)
    heads = ["Mina", "Estado", "Situación", "Tipo", "Accidentes", "Infracciones", "Multa pagada", "Tasa 2000–2026", "Tendencia de accidentes"]
    for j, h in enumerate(heads):
        ws_min.write(4, 1 + j, h, f_head)
    for i, row in minas.iterrows():
        r = 5 + i
        xr = r + 1
        sub = _rows(a, 0, 9999, row["mina"])
        ws_min.write(r, 1, row["mina"], f_cell)
        ws_min.write_formula(r, 2, f"=XLOOKUP($B{xr},t_minas[Mina],t_minas[Estado],\"\")", f_cell, row["estado"])
        ws_min.write_formula(r, 3, f"=XLOOKUP($B{xr},t_minas[Mina],t_minas[Situación],\"\")", f_cell, row["situacion"])
        ws_min.write_formula(r, 4, f"=XLOOKUP($B{xr},t_minas[Mina],t_minas[Tipo],\"\")", f_cell, row["tipo"])
        ws_min.write_formula(r, 5, f"=SUMIFS(t_anio_mina[Accidentes],t_anio_mina[Mina],$B{xr})", f_int, int(sub["accidentes"].sum()))
        ws_min.write_formula(r, 6, f"=SUMIFS(t_anio_mina[Infracciones],t_anio_mina[Mina],$B{xr})", f_int, int(sub["infracciones"].sum()))
        ws_min.write_formula(r, 7, f"=SUMIFS(t_anio_mina[Multa pagada],t_anio_mina[Mina],$B{xr})", f_int, float(sub["multa_pagada"].sum()))
        rt = _rate(sub) if sub["horas"].sum() >= MIN_HORAS_TASA else None
        ws_min.write_formula(
            r, 8,
            f'=IFERROR(IF(SUMIFS(t_anio_mina[Horas],t_anio_mina[Mina],$B{xr})<{MIN_HORAS_TASA},"s/d",'
            f'SUMIFS(t_anio_mina[Casos tasa],t_anio_mina[Mina],$B{xr})*200000/SUMIFS(t_anio_mina[Horas],t_anio_mina[Mina],$B{xr})),"s/d")',
            f_dec, round(rt, 6) if rt is not None else "s/d")
        ws_min.write(r, 9, "", f_cell)
        mr = mrow0 + i + 1
        ws_min.add_sparkline(r, 9, {"range": f"Calc!B{mr}:{xl_col_to_name(len(years))}{mr}", "type": "column", "series_color": COPPER,
                                    "high_point": True, "markers": False, "negative_points": False})
        ws_min.set_row(r, 20)
    last = 5 + n_min
    ws_min.conditional_format(5, 5, last - 1, 5, {"type": "data_bar", "bar_color": COPPER, "bar_solid": True, "bar_no_border": True})
    ws_min.conditional_format(5, 6, last - 1, 6, {"type": "data_bar", "bar_color": BLUE, "bar_solid": True, "bar_no_border": True})
    ws_min.conditional_format(5, 8, last - 1, 8, {"type": "2_color_scale", "min_color": "#FFFFFF", "max_color": COPPER})
    ws_min.autofilter(4, 1, last - 1, 9)
    ws_min.freeze_panes(5, 2)
    ws_min.set_landscape()
    ws_min.set_paper(9)
    ws_min.fit_to_pages(1, 0)
    ws_min.repeat_rows(4)

    # ------------------------------------------------------------ Pivote (the PivotTables and slicers are added inside Excel)
    ws_piv.set_column("A:A", 2)
    ws_piv.set_column("B:B", 36)
    ws_piv.set_column("C:G", 14)
    ws_piv.set_column("H:H", 3)
    ws_piv.set_column("I:I", 20)
    ws_piv.set_column("J:M", 14)
    ws_piv.set_row(0, 34)
    ws_piv.write("B1", "Tablas dinámicas y segmentadores", f_title)
    ws_piv.merge_range("B2:M2", "Esta hoja se completa dentro de Excel: tablas dinámicas y segmentadores sobre la tabla t_anio_mina (pasos en excel/PASOS_MANUALES.md).", f_sub)

    # ------------------------------------------------------------ Inicio
    ws_ini.set_column("A:A", 3)
    ws_ini.set_column("B:B", 110)
    ws_ini.set_row(0, 40)
    ws_ini.write("B1", "Seguridad minera (MSHA): panel en Excel", f_title)
    ws_ini.write("B2", "Cifras agregadas de los datos públicos de MSHA (EE. UU.) para las 43 minas de Freeport-McMoRan, 2000 a 2026", f_sub)
    ws_ini.write("B4", "Qué es", f_h2)
    ws_ini.write("B5", "Un panel en Excel hecho con las mismas cifras del informe de Power BI del repositorio: tarjetas, cuatro gráficos nativos "
                       "y una tabla de minas con minigráficos. Cambia el año o la mina en la hoja Panel y todo se recalcula.", f_txt)
    ws_ini.set_row(4, 34)
    ws_ini.write("B7", "Cómo usarlo", f_h2)
    ws_ini.write("B8", "1. Ve a la hoja Panel y elige un año y una mina en las celdas con borde naranja.", f_txt)
    ws_ini.write("B9", "2. Mira la hoja Minas para comparar las 43 minas (barras de datos y tendencia).", f_txt)
    ws_ini.write("B10", "3. En Datos están las tres tablas con nombre; en Cómo está hecho, las técnicas usadas.", f_txt)
    ws_ini.write_url("B12", "internal:'Panel'!A1", f_link, "Ir al Panel")
    ws_ini.write_url("B13", "internal:'Minas'!A1", f_link, "Ir a Minas")
    ws_ini.write_url("B14", "internal:'Cómo está hecho'!A1", f_link, "Ir a Cómo está hecho")
    ws_ini.write("B16", "Fuente y límites", f_h2)
    ws_ini.write("B17", f"Fuente: MSHA Open Government Data Sets; foto del {snapshot}. La tasa de incidencia se calcula con el personal propio y solo en "
                        "trimestres con horas; MSHA no publica toneladas para estas minas. El libro lleva solo cifras agregadas, no los registros originales. "
                        "Proyecto independiente, sin afiliación con MSHA ni Freeport-McMoRan.", f_txt)
    ws_ini.set_row(16, 62)

    # ------------------------------------------------------------ Cómo está hecho
    ws_how.set_column("A:A", 3)
    ws_how.set_column("B:B", 26)
    ws_how.set_column("C:C", 62)
    ws_how.set_column("D:D", 42)
    ws_how.write("B1", "Cómo está hecho", f_title)
    ws_how.write("B2", "Qué técnica de Excel usa cada parte y dónde verla", f_sub)
    for j, h in enumerate(["Parte", "Técnica", "Dónde verla"]):
        ws_how.write(3, 1 + j, h, f_head)
    rows = [
        ("Tablas con nombre", "Tres tablas de Excel (t_anio_mina, t_gravedad, t_minas) y referencias estructuradas en todas las fórmulas.", "Hoja Datos; fórmulas de Panel y Calc"),
        ("Listas desplegables", "Validación de datos con listas de años y de minas; los nombres selAnio y selMina guardan la elección.", "Panel, celdas D4 y H4"),
        ("Sumas condicionales", "SUMIFS con rangos de año (desde/hasta) y comodín * para «todas las minas».", "Panel (tarjetas) y hoja Calc"),
        ("Búsquedas", "XLOOKUP para traer estado, situación y tipo de la mina; INDEX y MATCH con LARGE para el ranking.", "Panel B5, hoja Minas, Calc I7:L12"),
        ("Tasa de incidencia", "Casos × 200.000 / horas con IFERROR; los años sin horas muestran «s/d».", "Tarjeta de tasa y gráfico combinado"),
        ("Gráficos nativos", "Columnas con año resaltado, líneas en eje secundario, barras ordenadas y anillo; títulos que siguen la selección.", "Panel, cuatro gráficos"),
        ("Formato condicional", "Barras de datos y escala de color en la tabla de minas.", "Hoja Minas"),
        ("Minigráficos", "Una columna de tendencia por mina, leída de la matriz mina × año.", "Hoja Minas, columna J"),
        ("Datos de origen", "Consultas SQL sobre las vistas rpt de SQL Server; el generador es excel/build_excel.py (Python, XlsxWriter).", "Repositorio, carpeta excel/"),
    ]
    for i, (p, t, d) in enumerate(rows):
        ws_how.write(4 + i, 1, p, F(bold=True, border=1, border_color=LINE, valign="top", text_wrap=True))
        ws_how.write(4 + i, 2, t, F(border=1, border_color=LINE, valign="top", text_wrap=True))
        ws_how.write(4 + i, 3, d, F(border=1, border_color=LINE, valign="top", text_wrap=True))
        ws_how.set_row(4 + i, 44)

    ws_pan.activate()
    wb.close()
    return {"accidentes": int(cur["accidentes"].sum()), "fatalidades": int(cur["fatalidades"].sum()),
            "infracciones": int(cur["infracciones"].sum()), "multa_pagada": float(cur["multa_pagada"].sum()),
            "horas": int(cur["horas"].sum()), "tasa": _rate(cur), "top": [(t[1], t[2]) for t in top], "n_minas": n_min}


def snapshot_date() -> str | None:
    """Date of the MSHA files used (latest `remote_last_modified` in data/manifest.json), or None if the manifest is missing."""
    import json
    from email.utils import parsedate_to_datetime

    path = HERE.parent / "data" / "manifest.json"
    if not path.exists():
        return None
    sets = json.loads(path.read_text(encoding="utf-8")).get("msha", {}).get("sets", {})
    dates = [parsedate_to_datetime(s["remote_last_modified"]).date() for s in sets.values() if s.get("remote_last_modified")]
    return max(dates).isoformat() if dates else None


def main() -> int:
    import datos

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--anio", default="Todos", help="year selected when the workbook opens (default: Todos)")
    ap.add_argument("--mina", default="Todas", help="mine selected when the workbook opens (default: Todas)")
    args = ap.parse_args()
    if not datos.container_ready():
        raise SystemExit("Falta el contenedor de SQL Server: docker compose up -d --wait")
    frames = datos.load_frames()
    summary = build_workbook(frames, args.out, args.anio, args.mina, snapshot=snapshot_date())
    print(f"-> {args.out}")
    print({k: v for k, v in summary.items() if k != "top"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
