-- Rules that constraints cannot express. A query returns rows only when a check FAILS.
USE MiningOpsSafety;
SET NOCOUNT ON;

-- the calendar is continuous and starts in 2000
SELECT 'dim_date is continuous from 2000-01-01' AS check_name,
       CONCAT(COUNT(*), ' rows between ', MIN(calendar_date), ' and ', MAX(calendar_date)) AS detail
FROM dwh.dim_date
HAVING MIN(calendar_date) <> '2000-01-01' OR COUNT(*) <> DATEDIFF(DAY, MIN(calendar_date), MAX(calendar_date)) + 1
UNION ALL
-- event dates are not in the future
SELECT 'accident dates not in the future', CONCAT(COUNT(*), ' accidents after today')
FROM dwh.fact_accident WHERE accident_date > CAST(GETDATE() AS DATE) HAVING COUNT(*) > 0
UNION ALL
SELECT 'violation issue dates not in the future', CONCAT(COUNT(*), ' violations after today')
FROM dwh.fact_violation WHERE issue_date > CAST(GETDATE() AS DATE) HAVING COUNT(*) > 0
UNION ALL
SELECT 'inspection dates not in the future', CONCAT(COUNT(*), ' inspections after today')
FROM dwh.fact_inspection WHERE begin_date > CAST(GETDATE() AS DATE) HAVING COUNT(*) > 0
UNION ALL
-- chronology
SELECT 'violation terminated before it was issued', CONCAT(COUNT(*), ' violations')
FROM dwh.fact_violation WHERE termination_date < issue_date HAVING COUNT(*) > 0
UNION ALL
-- numeric sanity
SELECT 'negative days lost or injuries', CONCAT(COUNT(*), ' accidents')
FROM dwh.fact_accident WHERE days_lost < 0 OR injuries_reported < 0 HAVING COUNT(*) > 0
UNION ALL
SELECT 'negative penalties', CONCAT(COUNT(*), ' violations')
FROM dwh.fact_violation WHERE proposed_penalty < 0 OR paid_penalty < 0 OR current_assessment < 0 HAVING COUNT(*) > 0
UNION ALL
SELECT 'negative or zero hours rows with employees', CONCAT(COUNT(*), ' workforce rows')
FROM dwh.fact_workforce WHERE hours_worked < 0 HAVING COUNT(*) > 0
UNION ALL
-- dimensions
SELECT 'exactly one target company flagged or more (none found)', '0 companies flagged'
WHERE NOT EXISTS (SELECT 1 FROM dwh.dim_company WHERE is_target_company = 1)
UNION ALL
SELECT 'coordinates inside valid ranges', CONCAT(COUNT(*), ' mines')
FROM dwh.dim_mine WHERE has_coordinates = 1 AND (latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180)
HAVING COUNT(*) > 0
UNION ALL
SELECT 'every reporting view exists', CONCAT(t.n, ' dwh tables vs ', v.n, ' rpt views')
FROM (SELECT COUNT(*) n FROM sys.tables WHERE schema_id = SCHEMA_ID('dwh') AND name <> 'etl_log') t
CROSS JOIN (SELECT COUNT(*) n FROM sys.views WHERE schema_id = SCHEMA_ID('rpt')) v
WHERE t.n <> v.n;
