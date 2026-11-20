-- Read-only login for Power BI. The password comes from the sqlcmd variable PBI_READER_PASSWORD (.env), never from the repo.
USE master;
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'pbi_reader')
    CREATE LOGIN pbi_reader WITH PASSWORD = N'$(PBI_READER_PASSWORD)', DEFAULT_DATABASE = MiningOpsSafety;
ELSE
    ALTER LOGIN pbi_reader WITH PASSWORD = N'$(PBI_READER_PASSWORD)';
GO
USE MiningOpsSafety;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'pbi_reader')
    CREATE USER pbi_reader FOR LOGIN pbi_reader;
GRANT SELECT ON SCHEMA::rpt TO pbi_reader;
GO
