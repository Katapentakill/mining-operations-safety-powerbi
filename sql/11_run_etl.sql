USE MiningOpsSafety;
GO
EXEC dwh.usp_load_all;
GO
SELECT table_name, row_count
FROM dwh.etl_log
WHERE run_id = (SELECT MAX(run_id) FROM dwh.etl_log)
ORDER BY table_name;
GO
