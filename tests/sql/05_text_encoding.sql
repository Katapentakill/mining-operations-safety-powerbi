-- Accents must survive the CSV -> staging -> dwh path. A query returns rows only when a check FAILS.
-- Mojibake signs: UTF-8 bytes read as CP437 give box-drawing characters (U+2500 to U+257F);
-- read as CP1252 they give a capital A with tilde followed by another symbol.
USE MiningOpsSafety;
SET NOCOUNT ON;

SELECT 'database collation is UTF-8' AS check_name, CAST(DATABASEPROPERTYEX(N'MiningOpsSafety', 'Collation') AS NVARCHAR(100)) AS detail
WHERE CAST(DATABASEPROPERTYEX(N'MiningOpsSafety', 'Collation') AS NVARCHAR(100)) COLLATE Latin1_General_BIN2 <> N'Latin1_General_100_CI_AS_SC_UTF8'
UNION ALL
SELECT 'no box-drawing mojibake in staged narratives', CONCAT(COUNT(*), ' rows')
FROM stg.accidents
WHERE PATINDEX(N'%[' + NCHAR(9472) + N'-' + NCHAR(9599) + N']%' COLLATE Latin1_General_BIN2, CAST(NARRATIVE AS NVARCHAR(MAX))) > 0
HAVING COUNT(*) > 0
UNION ALL
SELECT 'no A-tilde mojibake in staged narratives', CONCAT(COUNT(*), ' rows')
FROM stg.accidents
WHERE CAST(NARRATIVE AS NVARCHAR(MAX)) COLLATE Latin1_General_BIN2 LIKE N'%' + NCHAR(195) + N'%'
HAVING COUNT(*) > 0
UNION ALL
SELECT 'no box-drawing mojibake in loaded narratives', CONCAT(COUNT(*), ' rows')
FROM dwh.accident_narrative
WHERE PATINDEX(N'%[' + NCHAR(9472) + N'-' + NCHAR(9599) + N']%' COLLATE Latin1_General_BIN2, narrative) > 0
HAVING COUNT(*) > 0;
