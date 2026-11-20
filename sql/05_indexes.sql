-- Non-clustered indexes on the foreign keys most used by the report filters and joins.
USE MiningOpsSafety;
GO
DROP INDEX IF EXISTS IX_fact_accident_date    ON dwh.fact_accident;
DROP INDEX IF EXISTS IX_fact_accident_mine    ON dwh.fact_accident;
DROP INDEX IF EXISTS IX_fact_violation_date   ON dwh.fact_violation;
DROP INDEX IF EXISTS IX_fact_violation_mine   ON dwh.fact_violation;
DROP INDEX IF EXISTS IX_fact_inspection_date  ON dwh.fact_inspection;
DROP INDEX IF EXISTS IX_fact_inspection_mine  ON dwh.fact_inspection;
DROP INDEX IF EXISTS IX_fact_workforce_date   ON dwh.fact_workforce;
GO
CREATE INDEX IX_fact_accident_date   ON dwh.fact_accident (date_key)  INCLUDE (injuries_reported, days_lost, injury_degree_key);
CREATE INDEX IX_fact_accident_mine   ON dwh.fact_accident (mine_key)  INCLUDE (date_key, injuries_reported);
CREATE INDEX IX_fact_violation_date  ON dwh.fact_violation (date_key) INCLUDE (proposed_penalty, paid_penalty, violation_profile_key);
CREATE INDEX IX_fact_violation_mine  ON dwh.fact_violation (mine_key) INCLUDE (date_key);
CREATE INDEX IX_fact_inspection_date ON dwh.fact_inspection (date_key) INCLUDE (inspection_hours, on_site_hours);
CREATE INDEX IX_fact_inspection_mine ON dwh.fact_inspection (mine_key) INCLUDE (date_key);
CREATE INDEX IX_fact_workforce_date  ON dwh.fact_workforce (date_key) INCLUDE (mine_key, work_area_key, hours_worked, avg_employees);
GO
