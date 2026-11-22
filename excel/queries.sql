-- Aggregated figures for the Excel workbook (one query per `-- name:` block). They read only the `rpt` views, like Power BI.
-- No raw rows leave the database: MSHA publishes no licence for its data, so the workbook carries aggregates only.

-- name: anio_mina
-- One row per mine and year with accidents, fatalities, injury cases for the incidence rate (own staff, quarters with hours),
-- violations, paid penalty and hours worked.
WITH dm AS (
    -- two different mines share a name in MSHA: add the mine id so that names are unique
    SELECT mine_key, CASE WHEN COUNT(*) OVER (PARTITION BY mine_name) > 1 THEN mine_name + N' (' + mine_id + N')' ELSE mine_name END AS mine_name
    FROM rpt.dim_mine
), acc AS (
    SELECT f.mine_key, YEAR(f.accident_date) AS anio,
           COUNT(*) AS accidentes,
           SUM(CASE WHEN g.is_fatality = 1 THEN 1 ELSE 0 END) AS fatalidades,
           SUM(CASE WHEN g.counts_as_injury = 1 AND f.is_contractor = 0 AND d.has_hours_data = 1 THEN 1 ELSE 0 END) AS casos_tasa,
           SUM(COALESCE(f.days_lost, 0)) AS dias_perdidos
    FROM rpt.fact_accident f
    JOIN rpt.dim_injury_degree g ON g.injury_degree_key = f.injury_degree_key
    JOIN rpt.dim_date d ON d.date_key = f.date_key
    GROUP BY f.mine_key, YEAR(f.accident_date)
), vio AS (
    SELECT mine_key, YEAR(issue_date) AS anio, COUNT(*) AS infracciones, SUM(COALESCE(paid_penalty, 0)) AS multa_pagada
    FROM rpt.fact_violation
    GROUP BY mine_key, YEAR(issue_date)
), hrs AS (
    SELECT mine_key, calendar_year AS anio, SUM(hours_worked) AS horas
    FROM rpt.fact_workforce
    GROUP BY mine_key, calendar_year
)
SELECT m.mine_name AS mina, k.anio,
       COALESCE(a.accidentes, 0) AS accidentes,
       COALESCE(a.fatalidades, 0) AS fatalidades,
       COALESCE(a.casos_tasa, 0) AS casos_tasa,
       COALESCE(a.dias_perdidos, 0) AS dias_perdidos,
       COALESCE(v.infracciones, 0) AS infracciones,
       COALESCE(v.multa_pagada, 0) AS multa_pagada,
       COALESCE(h.horas, 0) AS horas
FROM (SELECT mine_key, anio FROM acc UNION SELECT mine_key, anio FROM vio UNION SELECT mine_key, anio FROM hrs) k
JOIN dm m ON m.mine_key = k.mine_key
LEFT JOIN acc a ON a.mine_key = k.mine_key AND a.anio = k.anio
LEFT JOIN vio v ON v.mine_key = k.mine_key AND v.anio = k.anio
LEFT JOIN hrs h ON h.mine_key = k.mine_key AND h.anio = k.anio
ORDER BY m.mine_name, k.anio;

-- name: gravedad
-- Accidents by mine, year and severity group (4 groups, in severity order).
WITH dm AS (
    -- two different mines share a name in MSHA: add the mine id so that names are unique
    SELECT mine_key, CASE WHEN COUNT(*) OVER (PARTITION BY mine_name) > 1 THEN mine_name + N' (' + mine_id + N')' ELSE mine_name END AS mine_name
    FROM rpt.dim_mine
)
SELECT m.mine_name AS mina, YEAR(f.accident_date) AS anio, g.degree_group_es AS grupo, g.degree_group_sort AS orden, COUNT(*) AS accidentes
FROM rpt.fact_accident f
JOIN rpt.dim_injury_degree g ON g.injury_degree_key = f.injury_degree_key
JOIN dm m ON m.mine_key = f.mine_key
GROUP BY m.mine_name, YEAR(f.accident_date), g.degree_group_es, g.degree_group_sort
ORDER BY m.mine_name, anio, orden;

-- name: minas
-- One row per mine.
SELECT CASE WHEN COUNT(*) OVER (PARTITION BY mine_name) > 1 THEN mine_name + N' (' + mine_id + N')' ELSE mine_name END AS mina,
       COALESCE(state_name, N'') AS estado, mine_status_es AS situacion, mine_type_es AS tipo,
       COALESCE(employees_reported, 0) AS empleados
FROM rpt.dim_mine
ORDER BY mina;

-- name: control
-- Control totals used to check the workbook against the database.
SELECT (SELECT COUNT(*) FROM rpt.fact_accident) AS accidentes,
       (SELECT COUNT(*) FROM rpt.fact_accident f JOIN rpt.dim_injury_degree g ON g.injury_degree_key = f.injury_degree_key WHERE g.is_fatality = 1) AS fatalidades,
       (SELECT COUNT(*) FROM rpt.fact_violation) AS infracciones,
       (SELECT COALESCE(SUM(paid_penalty), 0) FROM rpt.fact_violation) AS multa_pagada,
       (SELECT COALESCE(SUM(hours_worked), 0) FROM rpt.fact_workforce) AS horas;
