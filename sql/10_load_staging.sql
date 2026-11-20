-- Loads the staging tables. The files in /data/load are written by scripts/04_load_sqlserver.py:
-- UTF-16 (widechar), pipe-delimited, header in row 1. $(COMPANY_SLUG) is a sqlcmd variable (config.toml).
-- Why not the UTF-8 CSV files? SQL Server on Linux has no CODEPAGE option and reads UTF-8 bytes
-- with the wrong code page, which corrupts accents.
USE MiningOpsSafety;
GO
SET NOCOUNT ON;

TRUNCATE TABLE stg.mines;
BULK INSERT stg.mines FROM '/data/load/$(COMPANY_SLUG)/mines.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.accidents;
BULK INSERT stg.accidents FROM '/data/load/$(COMPANY_SLUG)/accidents.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.inspections;
BULK INSERT stg.inspections FROM '/data/load/$(COMPANY_SLUG)/inspections.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.violations;
BULK INSERT stg.violations FROM '/data/load/$(COMPANY_SLUG)/violations.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.assessed_violations;
BULK INSERT stg.assessed_violations FROM '/data/load/$(COMPANY_SLUG)/assessed_violations.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.mines_prod_yearly;
BULK INSERT stg.mines_prod_yearly FROM '/data/load/$(COMPANY_SLUG)/mines_prod_yearly.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.mines_prod_quarterly;
BULK INSERT stg.mines_prod_quarterly FROM '/data/load/$(COMPANY_SLUG)/mines_prod_quarterly.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.controller_operator_history;
BULK INSERT stg.controller_operator_history FROM '/data/load/$(COMPANY_SLUG)/controller_operator_history.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.cu_price_monthly;
BULK INSERT stg.cu_price_monthly FROM '/data/load/chile_context/cu_price_monthly.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);

TRUNCATE TABLE stg.cu_production_monthly;
BULK INSERT stg.cu_production_monthly FROM '/data/load/chile_context/cu_production_monthly.txt'
    WITH (FIRSTROW = 2, FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', DATAFILETYPE = 'widechar', KEEPNULLS, TABLOCK);
GO
