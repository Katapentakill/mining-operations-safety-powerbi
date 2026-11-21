# Decisions and known limits

Each item says what was decided and why. Items marked **verify** are assumptions to check before publishing numbers.

## Data

1. **Real data, one company.** MSHA publishes mine-level data for every US mine. The company is the *current controller* of a mine in `Mines`; event and workforce tables are filtered by `MINE_ID`, so the history of those mines since 2000 is included, also years in which another controller (for example Phelps Dodge) ran them. `dim_company.is_target_company` and `fact_accident.is_target_company_era` keep that distinction.
2. **No tonnage.** `ANNUAL_COAL_PROD` and `COAL_PRODUCTION` are zero or empty for every row of these mines. The project is about workforce, safety and compliance. Production, grade and equipment data from a real mine are not public.
3. **Contractors.** 1,482 accidents involve a contractor, but contractor hours have no `MINE_ID`. The incidence rate therefore uses own staff only; contractor accidents are shown separately.
4. **Violations and penalties.** `assessed_violations` is 1:1 with `violations` (18,719 of 19,046 violations have a penalty), so they are one fact with a `LEFT JOIN`. Penalty amounts come from `assessed_violations`; its proposed total differs by 100 dollars from the violations table.
5. **Quarterly hours.** Quarterly hours add up exactly to the yearly table wherever both exist, and the quarterly table has 61 more mine-area-year groups, so quarterly is the source.
6. **Partial year.** Violations and accidents reach November 2026 but workforce hours stop at the third quarter. Rates use `dim_date.has_hours_data` so accidents are never divided by missing hours.
7. **Dates.** Source dates are `mm/dd/yyyy` text; `TRY_CONVERT(date, x, 101)` after `NULLIF(x, '')`, because converting an empty string gives 1900-01-01 (dates) or 0 (numbers).

## KPIs

8. **Incidence rate** = injury cases of own staff x 200,000 / hours worked. **Verify** against MSHA's published definition before using the figure in public.
9. **`counts_as_injury`** = degree of injury 01 to 06 and **`is_lost_time`** = 01 to 04. **Verify**; both are flags in `dim_injury_degree`, so they can be changed in one place.
10. **Monthly rates are not offered.** Hours are stored per quarter (on the first day of the quarter). Use year or quarter for rates.
11. `INJ_ILLNESS` in violations is the gravity the inspector expected (`Fatal`, `Permanent`...), not an actual outcome; it is exposed as `expected_injury`.

## Engineering

12. **Accents and `BULK INSERT` on Linux.** SQL Server for Linux has no `CODEPAGE` option and reads UTF-8 bytes with the wrong code page (the ¼ in one narrative came out as two box-drawing characters). Neither `nvarchar` columns nor a UTF-8 database collation fixed it. The loader therefore writes a UTF-16, pipe-delimited copy of each CSV (`data/load/`) and uses `DATAFILETYPE = 'widechar'`, which loads correctly. It refuses fields that contain a pipe or a line break. `tests/sql/05_text_encoding.sql` fails if mojibake appears again; it caught this bug during development.
13. **Staging is text.** Every staging column is `varchar` in a UTF-8 database collation, so a bad value never stops a load; typing happens in the ETL, which fails loudly on inner-join losses (row counts are reconciled by tests).
14. **No `pyodbc`.** Loading uses `sqlcmd` inside the container, so the project needs only Docker and the Python standard library (plus `pandas` for profiling).
15. **TOML, not YAML.** `config.toml` is read with `tomllib` (Python 3.11+), avoiding a dependency.
16. **CSV bytes are preserved** (`.gitattributes`): the fixtures stay byte-identical to what the pipeline writes (UTF-8 with BOM, CRLF). The loader reads them with Python's `csv` module, so line endings no longer matter for `BULK INSERT`.
17. **No data in Git.** The MSHA page states no license, the raw files are 3.5 GB, and they change weekly. The pipeline downloads them; `data/manifest.json` records the snapshot.

## Power BI

18. **PBIP with TMDL and PBIR.** The model and report are text, so they can be reviewed in Git. The project was bootstrapped once by a generator and is now edited in Power BI Desktop; saving writes the text files again.
19. **Import mode** with parameters `Servidor` and `Base`; a `.pbit` template (no data) goes to GitHub Releases instead of a `.pbix`.
20. **Spanish captions, English sources.** Table and column names in the report are Spanish; `sourceColumn` keeps the English warehouse names.
21. `scripts/validate_pbip.py` checks that every `sourceColumn` exists in the DDL, every relationship and DAX reference exists, and every visual field exists. It cannot replace opening the project in Power BI Desktop.
22. **Scatter instead of a map.** Power BI Desktop disables the map visuals by default (a global security option), so *Map and mine detail* plots the 27 mines that have coordinates by longitude and latitude, sized by accidents: no basemap and no external service. The table next to it lists all 43 mines.
23. **One theme, one year filter.** The `Copper Mining` theme is registered in the report and styles titles, backgrounds and borders for every visual; the sidebar, the page navigator and the header are the same on all six pages. The year slicer belongs to one sync group, so choosing a year on one page filters the others.
24. **One company, one source (2026-11-21).** The report tells one story: MSHA as the publisher and the 43 mines controlled by Freeport-McMoRan. The Chile copper price and production context (Cochilco) was removed from scripts, SQL, model, report and tests: it covered other companies and never connected to the safety data. Four accident dimensions that no page showed (occupation, nature of injury, activity, equipment) were removed too. Kept on purpose: `dim_company` (it explains years in which another controller ran a mine) and `fact_inspection` (used in *Violations and penalties*). The raw MSHA files still hold the dropped columns, so a dimension can come back from `accidents.csv`.
25. **Spanish at the source (2026-11-21).** Report labels are translated in `sql/03_etl.sql` (`*_es` columns in `dim_mine`, `dim_work_area`, `dim_violation_profile`, `dim_accident_type`, `dim_body_part`), not visual by visual. The MSHA text and codes are kept; in Power BI the visible column points at the Spanish one and the original is a hidden column named `(MSHA, inglés)`. DAX that filters on a MSHA value (for example `S&S = "Yes"`) must use the hidden column. Accident types and body parts also have a *top* column (7 most frequent by count, the rest as *Otros tipos* / *Otras partes*, shown in gray) so charts need no scrolling; the ranking is computed at load time. `tests/sql/06_translations.sql` fails when a new MSHA code has no translation.
