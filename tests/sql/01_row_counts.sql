-- Staging -> dwh reconciliation. A query returns rows only when a check FAILS.
USE MiningOpsSafety;
SET NOCOUNT ON;

SELECT 'mines: staged vs loaded' AS check_name, CONCAT(s.n, ' vs ', f.n) AS detail
FROM (SELECT COUNT(*) n FROM stg.mines) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.dim_mine) f WHERE s.n <> f.n
UNION ALL
SELECT 'accidents: staged vs loaded', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM stg.accidents) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.fact_accident) f WHERE s.n <> f.n
UNION ALL
SELECT 'accident narratives: one per accident', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM dwh.fact_accident) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.accident_narrative) f WHERE s.n <> f.n
UNION ALL
SELECT 'violations: staged vs loaded', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM stg.violations) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.fact_violation) f WHERE s.n <> f.n
UNION ALL
SELECT 'violations with assessment: staged vs loaded', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM stg.assessed_violations) s
CROSS JOIN (SELECT COUNT(*) n FROM dwh.fact_violation WHERE has_assessment = 1) f WHERE s.n <> f.n
UNION ALL
SELECT 'inspections: staged vs loaded', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM stg.inspections) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.fact_inspection) f WHERE s.n <> f.n
UNION ALL
SELECT 'workforce quarters: staged vs loaded', CONCAT(s.n, ' vs ', f.n)
FROM (SELECT COUNT(*) n FROM stg.mines_prod_quarterly) s CROSS JOIN (SELECT COUNT(*) n FROM dwh.fact_workforce) f WHERE s.n <> f.n;
