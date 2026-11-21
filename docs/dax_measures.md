# DAX measures

40 measures, stored in the fact tables and grouped in display folders. The source of truth is the TMDL in `powerbi/MiningOperationsSafety.SemanticModel/definition/tables/`.

| Table | Folder | Measures |
|---|---|---|
| Accidentes | 1 Accidentes | Accidentes, Lesiones declaradas, Fatalidades, Casos con tiempo perdido, Días perdidos, Días restringidos, Accidentes de contratistas, % de accidentes de contratistas, Experiencia promedio en la mina (años) |
| Accidentes | 2 Tiempo | Accidentes año anterior, Variación vs año anterior, Accidentes acumulados del año, Accidentes últimos 12 meses |
| Accidentes | 3 Tasas | Casos de lesión (personal propio), Tasa de incidencia (por 200.000 h), Tasa de días perdidos (por 200.000 h) |
| Infracciones | 1 Infracciones | Infracciones, Infracciones S&S, % S&S, Personas afectadas, Días promedio para corregir |
| Infracciones | 2 Multas | Infracciones con multa, Multa propuesta, Multa vigente, Multa pagada, % de multa pagada, Multa promedio |
| Inspecciones | Inspecciones | Inspecciones, Horas de inspección, Horas en sitio, Infracciones por 100 h de inspección |
| Plantilla | Plantilla | Horas trabajadas, Empleados promedio, Horas por empleado |
| Accidentes, Infracciones, Mina | 9 Presentación | Accidentes (tabla), Infracciones (tabla), Multa pagada (tabla) (show "—" instead of blanks), Accidentes (Top 10 minas), Escala de burbuja (square root of accidents), Color por estado (hex color for the map) |

## The main rate

```dax
Tasa de incidencia (por 200.000 h) =
VAR Casos = CALCULATE ( [Casos de lesión (personal propio)], Fecha[Con horas disponibles] = TRUE () )
RETURN DIVIDE ( Casos * 200000, [Horas trabajadas] )
```

Own-staff injury cases (degree of injury 01 to 06, no contractor) in quarters that have hours, per 200,000 hours. Use year or quarter on the axis.

## Reconciliation with SQL (snapshot of 2026-11-19)

After refreshing, these values must match the report. Each one comes from a query against the `rpt` views.

| Check | Expected | SQL used |
|---|---|---|
| Accidentes (all years) | 6,654 | `SELECT COUNT(*) FROM rpt.fact_accident` |
| Fatalidades | 15 | `... JOIN rpt.dim_injury_degree ... WHERE is_fatality = 1` |
| Días perdidos | 97,916 | `SELECT SUM(days_lost) FROM rpt.fact_accident` |
| Infracciones | 19,046 | `SELECT COUNT(*) FROM rpt.fact_violation` |
| Multa propuesta | $14,301,764 | `SELECT SUM(proposed_penalty) FROM rpt.fact_violation` |
| Multa pagada | $12,223,998 | `SELECT SUM(paid_penalty) FROM rpt.fact_violation` |
| Horas de inspección | about 175,477 (rounded) | `SELECT SUM(inspection_hours) FROM rpt.fact_inspection` |
| Tasa de incidencia, año 2024 | 2.26 (236 cases, 20,839,543 hours) | see `docs/decisions.md`, item 8 |

Counts change when MSHA data are refreshed; the values above belong to the stored snapshot.
