-- Reporting layer: one view per dwh table (except the ETL log). Power BI reads only these.
-- Re-run this script after 02_dwh_tables.sql.
USE MiningOpsSafety;
GO
DECLARE @name SYSNAME;
DECLARE c CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID(N'dwh') AND name <> N'etl_log' ORDER BY name;
OPEN c;
FETCH NEXT FROM c INTO @name;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC (N'CREATE OR ALTER VIEW rpt.' + @name + N' AS SELECT * FROM dwh.' + @name);
    FETCH NEXT FROM c INTO @name;
END;
CLOSE c;
DEALLOCATE c;
GO
