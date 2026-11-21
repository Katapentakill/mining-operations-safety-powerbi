-- Star schema. Run once (it drops and recreates the tables); data is loaded by 03_etl.sql.
-- Conventions: surrogate keys *_key (INT), natural keys kept as *_id / *_code / *_no.
USE MiningOpsSafety;
GO

-- Facts first (they reference the dimensions)
DROP TABLE IF EXISTS dwh.accident_narrative, dwh.fact_accident, dwh.fact_violation, dwh.fact_inspection,
                     dwh.fact_workforce;
DROP TABLE IF EXISTS dwh.dim_mine, dwh.dim_company, dwh.dim_work_area, dwh.dim_injury_degree, dwh.dim_accident_type,
                     dwh.dim_body_part,
                     dwh.dim_standard, dwh.dim_violation_profile, dwh.dim_date;
DROP TABLE IF EXISTS dwh.etl_log;
GO

-- ------------------------------------------------------------------ dimensions
CREATE TABLE dwh.dim_date (
    date_key          INT           NOT NULL PRIMARY KEY,          -- yyyymmdd
    calendar_date     DATE          NOT NULL UNIQUE,
    calendar_year     SMALLINT      NOT NULL,
    calendar_quarter  TINYINT       NOT NULL,
    year_quarter      CHAR(7)       NOT NULL,                      -- 2024-Q1
    quarter_start     DATE          NOT NULL,
    calendar_month    TINYINT       NOT NULL,
    month_name_es     NVARCHAR(12)  NOT NULL,
    year_month        CHAR(7)       NOT NULL,                      -- 2024-03
    month_start       DATE          NOT NULL,
    weekday_number    TINYINT       NOT NULL,                      -- 1 = Monday
    weekday_name_es   NVARCHAR(12)  NOT NULL,
    fiscal_year       SMALLINT      NOT NULL,                      -- MSHA fiscal year starts on 1 October
    fiscal_quarter    TINYINT       NOT NULL,
    has_hours_data    BIT           NOT NULL DEFAULT 0             -- quarter covered by workforce hours
);

CREATE TABLE dwh.dim_mine (
    mine_key                  INT IDENTITY(1,1) PRIMARY KEY,
    mine_id                   VARCHAR(7)    NOT NULL UNIQUE,
    mine_name                 NVARCHAR(100) NOT NULL,
    mine_type                 NVARCHAR(20)  NULL,                  -- Surface / Underground / Facility
    mine_status               NVARCHAR(20)  NULL,
    mine_status_es            NVARCHAR(20)  NOT NULL,
    mine_type_es              NVARCHAR(30)  NOT NULL,
    state_name                NVARCHAR(20)  NULL,
    is_active                 BIT           NOT NULL,
    status_date               DATE          NULL,
    commodity                 NVARCHAR(80)  NULL,                  -- MSHA primary SIC description
    commodity_es              NVARCHAR(60)  NULL,
    state                     NCHAR(2)      NULL,
    county                    NVARCHAR(60)  NULL,
    latitude                  DECIMAL(9,6)  NULL,
    longitude                 DECIMAL(9,6)  NULL,
    has_coordinates           BIT           NOT NULL,
    employees_reported        INT           NULL,
    current_controller_id     VARCHAR(7)    NULL,
    current_controller_name   NVARCHAR(100) NULL,
    current_operator_id       VARCHAR(7)    NULL,
    current_operator_name     NVARCHAR(100) NULL
);

CREATE TABLE dwh.dim_company (                                     -- controller (parent company) at event time
    company_key        INT IDENTITY(1,1) PRIMARY KEY,
    controller_id      VARCHAR(7)    NOT NULL UNIQUE,              -- '?' = unknown
    controller_name    NVARCHAR(100) NOT NULL,
    is_target_company  BIT           NOT NULL                      -- the company this snapshot was built for
);

CREATE TABLE dwh.dim_work_area (
    work_area_key   INT IDENTITY(1,1) PRIMARY KEY,
    work_area_code  VARCHAR(3)    NOT NULL UNIQUE,
    work_area_desc  NVARCHAR(80)  NOT NULL,
    work_area_es    NVARCHAR(80)  NOT NULL,
    work_area_group NVARCHAR(20)  NOT NULL,                        -- Surface / Plant / Underground / Office / Other
    work_area_group_es NVARCHAR(20) NOT NULL
);

CREATE TABLE dwh.dim_injury_degree (
    injury_degree_key INT IDENTITY(1,1) PRIMARY KEY,
    degree_code       VARCHAR(3)    NOT NULL UNIQUE,
    degree_desc       NVARCHAR(80)  NOT NULL,
    degree_es         NVARCHAR(100) NOT NULL,
    degree_sort       TINYINT       NOT NULL,                      -- severity order; unknown last
    is_fatality       BIT           NOT NULL,
    is_lost_time      BIT           NOT NULL,                      -- degrees 01 to 04
    counts_as_injury  BIT           NOT NULL                       -- degrees 01 to 06 (assumption, see docs/decisions.md)
);

CREATE TABLE dwh.dim_accident_type (accident_type_key INT IDENTITY(1,1) PRIMARY KEY, accident_type_code VARCHAR(10) NOT NULL UNIQUE, accident_type_desc NVARCHAR(150) NOT NULL, accident_type_es NVARCHAR(150) NULL,
                                  accident_type_top NVARCHAR(150) NULL, accident_type_rank TINYINT NULL);
CREATE TABLE dwh.dim_body_part     (body_part_key     INT IDENTITY(1,1) PRIMARY KEY, body_part_code     VARCHAR(10) NOT NULL UNIQUE, body_part_desc     NVARCHAR(150) NOT NULL, body_part_es     NVARCHAR(150) NULL,
                                  body_part_top NVARCHAR(150) NULL, body_part_rank TINYINT NULL);

CREATE TABLE dwh.dim_standard (                                    -- safety standard cited (CFR part and section)
    standard_key  INT IDENTITY(1,1) PRIMARY KEY,
    part_section  VARCHAR(30) NOT NULL UNIQUE,                     -- e.g. 56.17001 ; '?' = unknown
    cfr_part      VARCHAR(10) NOT NULL                             -- e.g. 56
);

CREATE TABLE dwh.dim_violation_profile (                           -- junk dimension of low-cardinality attributes
    violation_profile_key        INT IDENTITY(1,1) PRIMARY KEY,
    significant_and_substantial  NVARCHAR(7)  NOT NULL,            -- Yes / No / Unknown
    negligence                   NVARCHAR(30) NOT NULL,
    likelihood                   NVARCHAR(30) NOT NULL,
    expected_injury              NVARCHAR(30) NOT NULL,            -- gravity expected by the inspector, not an actual outcome
    citation_type                NVARCHAR(30) NOT NULL,            -- Citation / Order
    significant_and_substantial_es NVARCHAR(12) NOT NULL,          -- Spanish labels shown in the report; the MSHA values above are kept
    negligence_es                NVARCHAR(30) NOT NULL,
    negligence_sort              TINYINT      NOT NULL,
    likelihood_es                NVARCHAR(30) NOT NULL,
    expected_injury_es           NVARCHAR(30) NOT NULL,
    citation_type_es             NVARCHAR(20) NOT NULL,
    mine_act_section             NVARCHAR(30) NOT NULL,
    CONSTRAINT UQ_violation_profile UNIQUE (significant_and_substantial, negligence, likelihood, expected_injury, citation_type, mine_act_section)
);

-- ------------------------------------------------------------------ facts
CREATE TABLE dwh.fact_accident (                                   -- grain: one reported accident (DOCUMENT_NO)
    accident_key            INT IDENTITY(1,1) PRIMARY KEY,
    document_no             VARCHAR(12)  NOT NULL UNIQUE,
    mine_key                INT NOT NULL REFERENCES dwh.dim_mine(mine_key),
    date_key                INT NOT NULL REFERENCES dwh.dim_date(date_key),
    company_key             INT NOT NULL REFERENCES dwh.dim_company(company_key),
    work_area_key           INT NOT NULL REFERENCES dwh.dim_work_area(work_area_key),
    injury_degree_key       INT NOT NULL REFERENCES dwh.dim_injury_degree(injury_degree_key),
    accident_type_key       INT NOT NULL REFERENCES dwh.dim_accident_type(accident_type_key),
    body_part_key           INT NOT NULL REFERENCES dwh.dim_body_part(body_part_key),
    accident_date           DATE NOT NULL,
    accident_hour           TINYINT NULL,                          -- NULL when MSHA stored 9999 (unknown)
    shift_start_hour        TINYINT NULL,
    is_contractor           BIT NOT NULL,
    is_target_company_era   BIT NOT NULL,                          -- controller at event time is the target company
    injuries_reported       INT NOT NULL,
    days_lost               INT NULL,
    days_restricted         INT NULL,
    schedule_charge         INT NULL,
    total_experience_years  DECIMAL(6,2) NULL,
    mine_experience_years   DECIMAL(6,2) NULL,
    job_experience_years    DECIMAL(6,2) NULL,
    return_to_work_date     DATE NULL
);

CREATE TABLE dwh.accident_narrative (
    accident_key  INT NOT NULL PRIMARY KEY REFERENCES dwh.fact_accident(accident_key),
    narrative     NVARCHAR(MAX) NULL
);

CREATE TABLE dwh.fact_violation (                                  -- grain: one violation; its penalty (if any) is on the same row
    violation_key            INT IDENTITY(1,1) PRIMARY KEY,
    event_no                 VARCHAR(12) NOT NULL,
    violation_no             VARCHAR(12) NOT NULL UNIQUE,
    mine_key                 INT NOT NULL REFERENCES dwh.dim_mine(mine_key),
    date_key                 INT NOT NULL REFERENCES dwh.dim_date(date_key),       -- issue date
    company_key              INT NOT NULL REFERENCES dwh.dim_company(company_key),
    standard_key             INT NOT NULL REFERENCES dwh.dim_standard(standard_key),
    violation_profile_key    INT NOT NULL REFERENCES dwh.dim_violation_profile(violation_profile_key),
    issue_date               DATE NOT NULL,
    occurrence_date          DATE NULL,
    termination_date         DATE NULL,
    final_order_date         DATE NULL,
    days_to_terminate        AS DATEDIFF(DAY, issue_date, termination_date),
    people_affected          INT NULL,
    has_assessment           BIT NOT NULL,
    proposed_penalty         DECIMAL(12,2) NULL,
    current_assessment       DECIMAL(12,2) NULL,
    paid_penalty             DECIMAL(12,2) NULL
);

CREATE TABLE dwh.fact_inspection (                                 -- grain: one inspection event
    inspection_key   INT IDENTITY(1,1) PRIMARY KEY,
    event_no         VARCHAR(12) NOT NULL UNIQUE,
    mine_key         INT NOT NULL REFERENCES dwh.dim_mine(mine_key),
    date_key         INT NOT NULL REFERENCES dwh.dim_date(date_key),       -- begin date
    company_key      INT NOT NULL REFERENCES dwh.dim_company(company_key),
    begin_date       DATE NOT NULL,
    end_date         DATE NULL,
    inspector_count  INT NULL,
    inspection_hours DECIMAL(10,2) NULL,
    on_site_hours    DECIMAL(10,2) NULL,
    activity_code    VARCHAR(10) NULL,
    activity         NVARCHAR(120) NULL
);

CREATE TABLE dwh.fact_workforce (                                  -- grain: mine x work area x quarter
    workforce_key     INT IDENTITY(1,1) PRIMARY KEY,
    mine_key          INT NOT NULL REFERENCES dwh.dim_mine(mine_key),
    work_area_key     INT NOT NULL REFERENCES dwh.dim_work_area(work_area_key),
    date_key          INT NOT NULL REFERENCES dwh.dim_date(date_key),     -- first day of the quarter
    calendar_year     SMALLINT NOT NULL,
    calendar_quarter  TINYINT NOT NULL,
    avg_employees     INT NULL,
    hours_worked      BIGINT NULL,
    CONSTRAINT UQ_fact_workforce UNIQUE (mine_key, work_area_key, date_key)
);

CREATE TABLE dwh.etl_log (
    run_id      INT NOT NULL,
    logged_at   DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    table_name  SYSNAME NOT NULL,
    row_count   INT NOT NULL
);
GO
