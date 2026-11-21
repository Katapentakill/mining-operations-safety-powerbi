-- ETL: stg (text) -> dwh (typed star schema). Full reload inside one transaction.
-- Empty strings are turned into NULL with NULLIF before any conversion, because
-- TRY_CONVERT('' to date) is 1900-01-01 and TRY_CONVERT('' to number) is 0.
USE MiningOpsSafety;
GO

CREATE OR ALTER PROCEDURE dwh.usp_load_all
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- ---------------------------------------------------------------- clear (facts first)
        DELETE FROM dwh.accident_narrative;
        DELETE FROM dwh.fact_accident;
        DELETE FROM dwh.fact_violation;
        DELETE FROM dwh.fact_inspection;
        DELETE FROM dwh.fact_workforce;
        DELETE FROM dwh.dim_mine;
        DELETE FROM dwh.dim_company;
        DELETE FROM dwh.dim_work_area;
        DELETE FROM dwh.dim_injury_degree;
        DELETE FROM dwh.dim_accident_type;
        DELETE FROM dwh.dim_body_part;
        DELETE FROM dwh.dim_standard;
        DELETE FROM dwh.dim_violation_profile;
        DELETE FROM dwh.dim_date;

        -- ---------------------------------------------------------------- dim_date
        DECLARE @start DATE = '2000-01-01';
        DECLARE @maxdata DATE = (SELECT MAX(d) FROM (VALUES
              ((SELECT MAX(TRY_CONVERT(DATE, NULLIF(ACCIDENT_DT, ''), 101)) FROM stg.accidents)),
              ((SELECT MAX(TRY_CONVERT(DATE, NULLIF(INSPECTION_BEGIN_DT, ''), 101)) FROM stg.inspections)),
              ((SELECT MAX(TRY_CONVERT(DATE, NULLIF(VIOLATION_ISSUE_DT, ''), 101)) FROM stg.violations))) AS t(d));
        DECLARE @endyear INT = (SELECT MAX(y) FROM (VALUES (YEAR(@maxdata)), (YEAR(GETDATE()))) AS t(y));
        DECLARE @end DATE = DATEFROMPARTS(@endyear, 12, 31);

        ;WITH nums AS (
            SELECT TOP (DATEDIFF(DAY, @start, @end) + 1)
                   ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
            FROM sys.all_objects a CROSS JOIN sys.all_objects b
        )
        INSERT dwh.dim_date (date_key, calendar_date, calendar_year, calendar_quarter, year_quarter, quarter_start,
                             calendar_month, month_name_es, year_month, month_start, weekday_number, weekday_name_es,
                             fiscal_year, fiscal_quarter)
        SELECT YEAR(x.d) * 10000 + MONTH(x.d) * 100 + DAY(x.d),
               x.d,
               YEAR(x.d),
               DATEPART(QUARTER, x.d),
               CONCAT(YEAR(x.d), '-Q', DATEPART(QUARTER, x.d)),
               DATEFROMPARTS(YEAR(x.d), (DATEPART(QUARTER, x.d) - 1) * 3 + 1, 1),
               MONTH(x.d),
               CHOOSE(MONTH(x.d), N'Enero', N'Febrero', N'Marzo', N'Abril', N'Mayo', N'Junio', N'Julio', N'Agosto',
                      N'Septiembre', N'Octubre', N'Noviembre', N'Diciembre'),
               CONCAT(YEAR(x.d), '-', RIGHT('0' + CAST(MONTH(x.d) AS VARCHAR(2)), 2)),
               DATEFROMPARTS(YEAR(x.d), MONTH(x.d), 1),
               (DATEDIFF(DAY, '1900-01-01', x.d) % 7) + 1,
               CHOOSE((DATEDIFF(DAY, '1900-01-01', x.d) % 7) + 1, N'Lunes', N'Martes', N'Miércoles', N'Jueves',
                      N'Viernes', N'Sábado', N'Domingo'),
               YEAR(x.d) + CASE WHEN MONTH(x.d) >= 10 THEN 1 ELSE 0 END,
               ((MONTH(x.d) + 2) % 12) / 3 + 1
        FROM nums CROSS APPLY (SELECT DATEADD(DAY, n, @start) AS d) x;

        -- ---------------------------------------------------------------- dim_mine
        INSERT dwh.dim_mine (mine_id, mine_name, mine_type, mine_status, is_active, status_date, commodity, state, county,
                             latitude, longitude, has_coordinates, employees_reported,
                             current_controller_id, current_controller_name, current_operator_id, current_operator_name)
        SELECT m.MINE_ID,
               COALESCE(NULLIF(m.CURRENT_MINE_NAME, ''), N'(unnamed)'),
               NULLIF(m.CURRENT_MINE_TYPE, ''),
               NULLIF(m.CURRENT_MINE_STATUS, ''),
               CASE WHEN m.CURRENT_MINE_STATUS = 'Active' THEN 1 ELSE 0 END,
               TRY_CONVERT(DATE, NULLIF(m.CURRENT_STATUS_DT, ''), 101),
               NULLIF(m.PRIMARY_SIC, ''),
               NULLIF(m.STATE, ''),
               NULLIF(m.FIPS_CNTY_NM, ''),
               c.lat, c.lon,
               CASE WHEN c.lat IS NOT NULL AND c.lon IS NOT NULL THEN 1 ELSE 0 END,
               TRY_CONVERT(INT, NULLIF(m.NO_EMPLOYEES, '')),
               NULLIF(m.CURRENT_CONTROLLER_ID, ''), NULLIF(m.CURRENT_CONTROLLER_NAME, ''),
               NULLIF(m.CURRENT_OPERATOR_ID, ''), NULLIF(m.CURRENT_OPERATOR_NAME, '')
        FROM stg.mines m
        CROSS APPLY (SELECT lat = TRY_CONVERT(DECIMAL(9,6), NULLIF(m.LATITUDE, '')),
                            lon = TRY_CONVERT(DECIMAL(9,6), NULLIF(m.LONGITUDE, ''))) c;

        -- ---------------------------------------------------------------- dim_company (controller at event time)
        INSERT dwh.dim_company (controller_id, controller_name, is_target_company)
        SELECT u.controller_id, MAX(u.controller_name),
               CASE WHEN u.controller_id IN (SELECT DISTINCT CURRENT_CONTROLLER_ID FROM stg.mines) THEN 1 ELSE 0 END
        FROM (
            SELECT CONTROLLER_ID AS controller_id, CONTROLLER_NAME AS controller_name FROM stg.accidents WHERE NULLIF(CONTROLLER_ID, '') IS NOT NULL
            UNION ALL
            SELECT CONTROLLER_ID, CONTROLLER_NAME FROM stg.inspections WHERE NULLIF(CONTROLLER_ID, '') IS NOT NULL
            UNION ALL
            SELECT CONTROLLER_ID, CONTROLLER_NAME FROM stg.violations WHERE NULLIF(CONTROLLER_ID, '') IS NOT NULL
            UNION ALL
            SELECT CONTROLLER_ID, CONTROLLER_NAME FROM stg.controller_operator_history WHERE NULLIF(CONTROLLER_ID, '') IS NOT NULL
        ) u
        GROUP BY u.controller_id;
        IF NOT EXISTS (SELECT 1 FROM dwh.dim_company WHERE controller_id = '?')
            INSERT dwh.dim_company (controller_id, controller_name, is_target_company) VALUES ('?', N'Unknown', 0);

        -- ---------------------------------------------------------------- dim_work_area
        INSERT dwh.dim_work_area (work_area_code, work_area_desc, work_area_es, work_area_group)
        SELECT u.code, MAX(u.descr),
               CASE u.code
                    WHEN '01' THEN N'Subterránea' WHEN '02' THEN N'Superficie de mina subterránea'
                    WHEN '03' THEN N'Rajo abierto / cantera' WHEN '04' THEN N'Barrena (auger)'
                    WHEN '05' THEN N'Botadero de residuos' WHEN '06' THEN N'Draga'
                    WHEN '12' THEN N'Otras operaciones mineras' WHEN '17' THEN N'Talleres o patios independientes'
                    WHEN '30' THEN N'Planta de procesamiento' WHEN '99' THEN N'Oficinas en la mina'
                    ELSE N'Sin clasificar' END,
               CASE WHEN u.code = '01' THEN N'Underground'
                    WHEN u.code IN ('02', '03', '04', '05', '06') THEN N'Surface'
                    WHEN u.code = '30' THEN N'Plant'
                    WHEN u.code = '99' THEN N'Office'
                    ELSE N'Other' END
        FROM (
            SELECT COALESCE(NULLIF(SUBUNIT_CD, ''), '?') AS code, SUBUNIT AS descr FROM stg.accidents
            UNION ALL
            SELECT COALESCE(NULLIF(SUBUNIT_CD, ''), '?'), SUBUNIT FROM stg.mines_prod_quarterly
        ) u
        GROUP BY u.code;
        IF NOT EXISTS (SELECT 1 FROM dwh.dim_work_area WHERE work_area_code = '?')
            INSERT dwh.dim_work_area VALUES ('?', N'No value found', N'Sin clasificar', N'Other');

        -- ---------------------------------------------------------------- dim_injury_degree
        INSERT dwh.dim_injury_degree (degree_code, degree_desc, degree_es, is_fatality, is_lost_time, counts_as_injury)
        SELECT u.code, MAX(u.descr),
               CASE u.code
                    WHEN '00' THEN N'Solo accidente (sin lesión)' WHEN '01' THEN N'Fatalidad'
                    WHEN '02' THEN N'Incapacidad permanente total o parcial' WHEN '03' THEN N'Días fuera del trabajo'
                    WHEN '04' THEN N'Días fuera y actividad restringida' WHEN '05' THEN N'Solo actividad restringida'
                    WHEN '06' THEN N'Sin días perdidos ni restricción' WHEN '07' THEN N'Enfermedad ocupacional'
                    WHEN '08' THEN N'Lesión por causas naturales' WHEN '09' THEN N'Lesión a no empleados'
                    WHEN '10' THEN N'Otros casos (incluye primeros auxilios)' ELSE N'Sin valor' END,
               CASE WHEN u.code = '01' THEN 1 ELSE 0 END,
               CASE WHEN u.code IN ('01', '02', '03', '04') THEN 1 ELSE 0 END,
               CASE WHEN u.code IN ('01', '02', '03', '04', '05', '06') THEN 1 ELSE 0 END
        FROM (SELECT COALESCE(NULLIF(DEGREE_INJURY_CD, ''), '?') AS code, DEGREE_INJURY AS descr FROM stg.accidents) u
        GROUP BY u.code;
        IF NOT EXISTS (SELECT 1 FROM dwh.dim_injury_degree WHERE degree_code = '?')
            INSERT dwh.dim_injury_degree VALUES ('?', N'NO VALUE FOUND', N'Sin valor', 0, 0, 0);

        -- ---------------------------------------------------------------- simple code dimensions (only those the report shows)
        INSERT dwh.dim_accident_type (accident_type_code, accident_type_desc)
        SELECT COALESCE(NULLIF(ACCIDENT_TYPE_CD, ''), '?'), MAX(COALESCE(NULLIF(ACCIDENT_TYPE, ''), N'No value found'))
        FROM stg.accidents GROUP BY COALESCE(NULLIF(ACCIDENT_TYPE_CD, ''), '?');
        IF NOT EXISTS (SELECT 1 FROM dwh.dim_accident_type WHERE accident_type_code = '?')
            INSERT dwh.dim_accident_type VALUES ('?', N'No value found');

        INSERT dwh.dim_body_part (body_part_code, body_part_desc)
        SELECT COALESCE(NULLIF(INJ_BODY_PART_CD, ''), '?'), MAX(COALESCE(NULLIF(INJ_BODY_PART, ''), N'No value found'))
        FROM stg.accidents GROUP BY COALESCE(NULLIF(INJ_BODY_PART_CD, ''), '?');
        IF NOT EXISTS (SELECT 1 FROM dwh.dim_body_part WHERE body_part_code = '?')
            INSERT dwh.dim_body_part VALUES ('?', N'No value found');

        -- ---------------------------------------------------------------- dim_standard and dim_violation_profile
        INSERT dwh.dim_standard (part_section, cfr_part)
        SELECT s.ps,
               LEFT(CASE WHEN CHARINDEX('.', s.ps) > 0 THEN LEFT(s.ps, CHARINDEX('.', s.ps) - 1) ELSE s.ps END, 10)
        FROM (SELECT DISTINCT COALESCE(NULLIF(PART_SECTION, ''), '?') AS ps FROM stg.violations) s;

        INSERT dwh.dim_violation_profile (significant_and_substantial, negligence, likelihood, expected_injury,
                                          citation_type, mine_act_section)
        SELECT DISTINCT n.sig, n.neg, n.lik, n.inj, n.cit, n.sec
        FROM stg.violations v
        CROSS APPLY (SELECT sig = CASE v.SIG_SUB WHEN 'Y' THEN N'Yes' WHEN 'N' THEN N'No' ELSE N'Unknown' END,
                            neg = COALESCE(NULLIF(v.NEGLIGENCE, ''), N'Unknown'),
                            lik = COALESCE(NULLIF(v.LIKELIHOOD, ''), N'Unknown'),
                            inj = COALESCE(NULLIF(v.INJ_ILLNESS, ''), N'Unknown'),
                            cit = COALESCE(NULLIF(v.CIT_ORD_SAFE, ''), N'Unknown'),
                            sec = COALESCE(NULLIF(v.SECTION_OF_ACT_1, ''), N'Unknown')) n;

        -- ---------------------------------------------------------------- fact_accident
        INSERT dwh.fact_accident (document_no, mine_key, date_key, company_key, work_area_key, injury_degree_key,
                                  accident_type_key, body_part_key, accident_date, accident_hour, shift_start_hour, is_contractor,
                                  is_target_company_era, injuries_reported, days_lost, days_restricted, schedule_charge,
                                  total_experience_years, mine_experience_years, job_experience_years, return_to_work_date)
        SELECT a.DOCUMENT_NO, m.mine_key,
               YEAR(d.v) * 10000 + MONTH(d.v) * 100 + DAY(d.v),
               co.company_key, wa.work_area_key, ind.injury_degree_key, aty.accident_type_key,
               bp.body_part_key,
               d.v,
               CASE WHEN a.ACCIDENT_TIME LIKE '[0-2][0-9][0-5][0-9]' AND LEFT(a.ACCIDENT_TIME, 2) < '24'
                    THEN CONVERT(TINYINT, LEFT(a.ACCIDENT_TIME, 2)) END,
               CASE WHEN a.SHIFT_BEGIN_TIME LIKE '[0-2][0-9][0-5][0-9]' AND LEFT(a.SHIFT_BEGIN_TIME, 2) < '24'
                    THEN CONVERT(TINYINT, LEFT(a.SHIFT_BEGIN_TIME, 2)) END,
               CASE WHEN NULLIF(a.CONTRACTOR_ID, '') IS NULL THEN 0 ELSE 1 END,
               co.is_target_company,
               COALESCE(TRY_CONVERT(INT, NULLIF(a.NO_INJURIES, '')), 0),
               TRY_CONVERT(INT, NULLIF(a.DAYS_LOST, '')),
               TRY_CONVERT(INT, NULLIF(a.DAYS_RESTRICT, '')),
               TRY_CONVERT(INT, NULLIF(a.SCHEDULE_CHARGE, '')),
               TRY_CONVERT(DECIMAL(6,2), NULLIF(a.TOT_EXPER, '')),
               TRY_CONVERT(DECIMAL(6,2), NULLIF(a.MINE_EXPER, '')),
               TRY_CONVERT(DECIMAL(6,2), NULLIF(a.JOB_EXPER, '')),
               TRY_CONVERT(DATE, NULLIF(a.RETURN_TO_WORK_DT, ''), 101)
        FROM stg.accidents a
        CROSS APPLY (SELECT v = TRY_CONVERT(DATE, NULLIF(a.ACCIDENT_DT, ''), 101)) d
        JOIN dwh.dim_mine m ON m.mine_id = a.MINE_ID
        JOIN dwh.dim_company co ON co.controller_id = COALESCE(NULLIF(a.CONTROLLER_ID, ''), '?')
        JOIN dwh.dim_work_area wa ON wa.work_area_code = COALESCE(NULLIF(a.SUBUNIT_CD, ''), '?')
        JOIN dwh.dim_injury_degree ind ON ind.degree_code = COALESCE(NULLIF(a.DEGREE_INJURY_CD, ''), '?')
        JOIN dwh.dim_accident_type aty ON aty.accident_type_code = COALESCE(NULLIF(a.ACCIDENT_TYPE_CD, ''), '?')
        JOIN dwh.dim_body_part bp ON bp.body_part_code = COALESCE(NULLIF(a.INJ_BODY_PART_CD, ''), '?');

        INSERT dwh.accident_narrative (accident_key, narrative)
        SELECT f.accident_key, NULLIF(a.NARRATIVE, '')
        FROM dwh.fact_accident f JOIN stg.accidents a ON a.DOCUMENT_NO = f.document_no;

        -- ---------------------------------------------------------------- fact_violation (+ penalty, 1:1)
        INSERT dwh.fact_violation (event_no, violation_no, mine_key, date_key, company_key, standard_key,
                                   violation_profile_key, issue_date, occurrence_date, termination_date, final_order_date,
                                   people_affected, has_assessment, proposed_penalty, current_assessment, paid_penalty)
        SELECT v.EVENT_NO, v.VIOLATION_NO, m.mine_key,
               YEAR(d.v) * 10000 + MONTH(d.v) * 100 + DAY(d.v),
               co.company_key, st.standard_key, vp.violation_profile_key,
               d.v,
               TRY_CONVERT(DATE, NULLIF(v.VIOLATION_OCCUR_DT, ''), 101),
               TRY_CONVERT(DATE, NULLIF(v.TERMINATION_DT, ''), 101),
               TRY_CONVERT(DATE, NULLIF(s.FINAL_ORDER_DT, ''), 101),
               TRY_CONVERT(INT, NULLIF(v.NO_AFFECTED, '')),
               CASE WHEN s.VIOLATION_NO IS NULL THEN 0 ELSE 1 END,
               TRY_CONVERT(DECIMAL(12,2), NULLIF(s.PROPOSED_PENALTY_AMT, '')),
               TRY_CONVERT(DECIMAL(12,2), NULLIF(s.CURRENT_ASSESSMENT_AMT, '')),
               TRY_CONVERT(DECIMAL(12,2), NULLIF(s.PAID_PROPOSED_PENALTY_AMT, ''))
        FROM stg.violations v
        CROSS APPLY (SELECT v = TRY_CONVERT(DATE, NULLIF(v.VIOLATION_ISSUE_DT, ''), 101)) d
        CROSS APPLY (SELECT sig = CASE v.SIG_SUB WHEN 'Y' THEN N'Yes' WHEN 'N' THEN N'No' ELSE N'Unknown' END,
                            neg = COALESCE(NULLIF(v.NEGLIGENCE, ''), N'Unknown'),
                            lik = COALESCE(NULLIF(v.LIKELIHOOD, ''), N'Unknown'),
                            inj = COALESCE(NULLIF(v.INJ_ILLNESS, ''), N'Unknown'),
                            cit = COALESCE(NULLIF(v.CIT_ORD_SAFE, ''), N'Unknown'),
                            sec = COALESCE(NULLIF(v.SECTION_OF_ACT_1, ''), N'Unknown')) n
        JOIN dwh.dim_mine m ON m.mine_id = v.MINE_ID
        JOIN dwh.dim_company co ON co.controller_id = COALESCE(NULLIF(v.CONTROLLER_ID, ''), '?')
        JOIN dwh.dim_standard st ON st.part_section = COALESCE(NULLIF(v.PART_SECTION, ''), '?')
        JOIN dwh.dim_violation_profile vp
             ON vp.significant_and_substantial = n.sig AND vp.negligence = n.neg AND vp.likelihood = n.lik
            AND vp.expected_injury = n.inj AND vp.citation_type = n.cit AND vp.mine_act_section = n.sec
        LEFT JOIN stg.assessed_violations s ON s.EVENT_NBR = v.EVENT_NO AND s.VIOLATION_NO = v.VIOLATION_NO;

        -- ---------------------------------------------------------------- fact_inspection
        INSERT dwh.fact_inspection (event_no, mine_key, date_key, company_key, begin_date, end_date, inspector_count,
                                    inspection_hours, on_site_hours, activity_code, activity)
        SELECT i.EVENT_NO, m.mine_key,
               YEAR(d.v) * 10000 + MONTH(d.v) * 100 + DAY(d.v),
               co.company_key, d.v,
               TRY_CONVERT(DATE, NULLIF(i.INSPECTION_END_DT, ''), 101),
               TRY_CONVERT(INT, NULLIF(i.NBR_INSPECTOR, '')),
               TRY_CONVERT(DECIMAL(10,2), NULLIF(i.TOTAL_INSP_HOURS, '')),
               TRY_CONVERT(DECIMAL(10,2), NULLIF(i.TOTAL_ON_SITE_HOURS, '')),
               NULLIF(i.ACTIVITY_CODE, ''), NULLIF(i.ACTIVITY, '')
        FROM stg.inspections i
        CROSS APPLY (SELECT v = TRY_CONVERT(DATE, NULLIF(i.INSPECTION_BEGIN_DT, ''), 101)) d
        JOIN dwh.dim_mine m ON m.mine_id = i.MINE_ID
        JOIN dwh.dim_company co ON co.controller_id = COALESCE(NULLIF(i.CONTROLLER_ID, ''), '?');

        -- ---------------------------------------------------------------- fact_workforce (quarterly)
        INSERT dwh.fact_workforce (mine_key, work_area_key, date_key, calendar_year, calendar_quarter, avg_employees, hours_worked)
        SELECT m.mine_key, wa.work_area_key,
               q.yr * 10000 + ((q.qtr - 1) * 3 + 1) * 100 + 1,
               q.yr, q.qtr,
               TRY_CONVERT(INT, NULLIF(w.AVG_EMPLOYEE_CNT, '')),
               TRY_CONVERT(BIGINT, NULLIF(w.HOURS_WORKED, ''))
        FROM stg.mines_prod_quarterly w
        CROSS APPLY (SELECT yr = TRY_CONVERT(SMALLINT, w.CAL_YR), qtr = TRY_CONVERT(TINYINT, w.CAL_QTR)) q
        JOIN dwh.dim_mine m ON m.mine_id = w.MINE_ID
        JOIN dwh.dim_work_area wa ON wa.work_area_code = COALESCE(NULLIF(w.SUBUNIT_CD, ''), '?');

        -- quarters up to the last one with hours can be used for rates
        UPDATE d SET has_hours_data = 1
        FROM dwh.dim_date d
        WHERE d.quarter_start <= (SELECT MAX(dd.calendar_date) FROM dwh.dim_date dd
                                  WHERE dd.date_key = (SELECT MAX(date_key) FROM dwh.fact_workforce));

        -- ---------------------------------------------------------------- log
        DECLARE @run INT = COALESCE((SELECT MAX(run_id) FROM dwh.etl_log), 0) + 1;
        INSERT dwh.etl_log (run_id, table_name, row_count)
        SELECT @run, t.n, t.c FROM (VALUES
            ('dim_date', (SELECT COUNT(*) FROM dwh.dim_date)),
            ('dim_mine', (SELECT COUNT(*) FROM dwh.dim_mine)),
            ('dim_company', (SELECT COUNT(*) FROM dwh.dim_company)),
            ('dim_standard', (SELECT COUNT(*) FROM dwh.dim_standard)),
            ('dim_violation_profile', (SELECT COUNT(*) FROM dwh.dim_violation_profile)),
            ('fact_accident', (SELECT COUNT(*) FROM dwh.fact_accident)),
            ('fact_violation', (SELECT COUNT(*) FROM dwh.fact_violation)),
            ('fact_inspection', (SELECT COUNT(*) FROM dwh.fact_inspection)),
            ('fact_workforce', (SELECT COUNT(*) FROM dwh.fact_workforce))) t(n, c);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
