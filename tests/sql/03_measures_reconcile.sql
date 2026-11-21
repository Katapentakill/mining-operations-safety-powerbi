-- Totals in the star schema must match the raw staging data. A query returns rows only when a check FAILS.
USE MiningOpsSafety;
SET NOCOUNT ON;

SELECT 'days lost: dwh vs staging' AS check_name, CONCAT(d.v, ' vs ', s.v) AS detail
FROM (SELECT COALESCE(SUM(days_lost), 0) v FROM dwh.fact_accident) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(INT, NULLIF(DAYS_LOST, ''))), 0) v FROM stg.accidents) s
WHERE d.v <> s.v
UNION ALL
SELECT 'injuries reported: dwh vs staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COALESCE(SUM(injuries_reported), 0) v FROM dwh.fact_accident) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(INT, NULLIF(NO_INJURIES, ''))), 0) v FROM stg.accidents) s
WHERE d.v <> s.v
UNION ALL
SELECT 'fatalities: dwh vs staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COUNT(*) v FROM dwh.fact_accident f JOIN dwh.dim_injury_degree g ON g.injury_degree_key = f.injury_degree_key WHERE g.is_fatality = 1) d
CROSS JOIN (SELECT COUNT(*) v FROM stg.accidents WHERE DEGREE_INJURY_CD = '01') s
WHERE d.v <> s.v
UNION ALL
SELECT 'proposed penalty: dwh vs assessed staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COALESCE(SUM(proposed_penalty), 0) v FROM dwh.fact_violation) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(DECIMAL(12,2), NULLIF(PROPOSED_PENALTY_AMT, ''))), 0) v FROM stg.assessed_violations) s
WHERE d.v <> s.v
UNION ALL
SELECT 'paid penalty: dwh vs assessed staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COALESCE(SUM(paid_penalty), 0) v FROM dwh.fact_violation) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(DECIMAL(12,2), NULLIF(PAID_PROPOSED_PENALTY_AMT, ''))), 0) v FROM stg.assessed_violations) s
WHERE d.v <> s.v
UNION ALL
SELECT 'inspection hours: dwh vs staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COALESCE(SUM(inspection_hours), 0) v FROM dwh.fact_inspection) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(DECIMAL(10,2), NULLIF(TOTAL_INSP_HOURS, ''))), 0) v FROM stg.inspections) s
WHERE d.v <> s.v
UNION ALL
SELECT 'hours worked: dwh vs staging', CONCAT(d.v, ' vs ', s.v)
FROM (SELECT COALESCE(SUM(hours_worked), 0) v FROM dwh.fact_workforce) d
CROSS JOIN (SELECT COALESCE(SUM(TRY_CONVERT(BIGINT, NULLIF(HOURS_WORKED, ''))), 0) v FROM stg.mines_prod_quarterly) s
WHERE d.v <> s.v
UNION ALL
-- quarterly hours add up to the yearly table wherever both exist
SELECT 'quarterly vs yearly hours differ', CONCAT(COUNT(*), ' mine/area/year groups')
FROM (
    SELECT q.MINE_ID, q.SUBUNIT_CD, q.CAL_YR,
           SUM(TRY_CONVERT(BIGINT, NULLIF(q.HOURS_WORKED, ''))) AS q_hours
    FROM stg.mines_prod_quarterly q
    GROUP BY q.MINE_ID, q.SUBUNIT_CD, q.CAL_YR
) qq
JOIN (
    SELECT y.MINE_ID, y.SUBUNIT_CD, y.CALENDAR_YR,
           SUM(TRY_CONVERT(BIGINT, NULLIF(y.ANNUAL_HRS, ''))) AS y_hours
    FROM stg.mines_prod_yearly y
    GROUP BY y.MINE_ID, y.SUBUNIT_CD, y.CALENDAR_YR
) yy ON yy.MINE_ID = qq.MINE_ID AND yy.SUBUNIT_CD = qq.SUBUNIT_CD AND yy.CALENDAR_YR = qq.CAL_YR
WHERE qq.q_hours <> yy.y_hours
HAVING COUNT(*) > 0;
