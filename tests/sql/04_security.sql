-- The Power BI login can read the reporting views and nothing else. A query returns rows only when a check FAILS.
USE MiningOpsSafety;
SET NOCOUNT ON;

DECLARE @result TABLE (check_name NVARCHAR(100), detail NVARCHAR(200));

EXECUTE AS USER = 'pbi_reader';
INSERT @result
SELECT 'pbi_reader can read rpt views', 'no SELECT on rpt.fact_accident'
WHERE HAS_PERMS_BY_NAME('rpt.fact_accident', 'OBJECT', 'SELECT') <> 1
UNION ALL
SELECT 'pbi_reader cannot read dwh tables', 'SELECT granted on dwh.fact_accident'
WHERE HAS_PERMS_BY_NAME('dwh.fact_accident', 'OBJECT', 'SELECT') = 1
UNION ALL
SELECT 'pbi_reader cannot read staging', 'SELECT granted on stg.accidents'
WHERE HAS_PERMS_BY_NAME('stg.accidents', 'OBJECT', 'SELECT') = 1
UNION ALL
SELECT 'pbi_reader cannot modify data', 'INSERT granted on dwh.fact_accident'
WHERE HAS_PERMS_BY_NAME('dwh.fact_accident', 'OBJECT', 'INSERT') = 1
UNION ALL
SELECT 'pbi_reader cannot run the ETL', 'EXECUTE granted on dwh.usp_load_all'
WHERE HAS_PERMS_BY_NAME('dwh.usp_load_all', 'OBJECT', 'EXECUTE') = 1;
REVERT;

SELECT check_name, detail FROM @result;
