-- Creates the database and the three schemas. Idempotent.
--   stg : staging, a 1:1 text copy of the CSV files
--   dwh : star schema (dimensions and facts)
--   rpt : views read by Power BI (the only schema the read-only login can see)
--
-- The database uses a UTF-8 collation so the varchar staging columns can hold any character.
-- (Accents survive the load because 10_load_staging.sql reads UTF-16 files, see that script.)
IF DB_ID(N'MiningOpsSafety') IS NULL
    CREATE DATABASE MiningOpsSafety COLLATE Latin1_General_100_CI_AS_SC_UTF8;
GO
IF CAST(DATABASEPROPERTYEX(N'MiningOpsSafety', 'Collation') AS NVARCHAR(100)) COLLATE Latin1_General_BIN2 <> N'Latin1_General_100_CI_AS_SC_UTF8'
    THROW 50001, N'MiningOpsSafety exists with another collation. Run: python scripts/04_load_sqlserver.py --reset-db', 1;
GO
ALTER DATABASE MiningOpsSafety SET RECOVERY SIMPLE;
GO
USE MiningOpsSafety;
GO
IF SCHEMA_ID(N'stg') IS NULL EXEC (N'CREATE SCHEMA stg');
IF SCHEMA_ID(N'dwh') IS NULL EXEC (N'CREATE SCHEMA dwh');
IF SCHEMA_ID(N'rpt') IS NULL EXEC (N'CREATE SCHEMA rpt');
GO
