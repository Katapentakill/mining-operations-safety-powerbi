-- Every Spanish presentation column is filled and no code is left without a translation (a missing
-- translation falls back to the MSHA text, so es = desc flags it). A check fails when its query returns rows.
USE MiningOpsSafety;
SELECT 'accident type without translation', accident_type_code FROM dwh.dim_accident_type
WHERE accident_type_es IS NULL OR accident_type_es = accident_type_desc
UNION ALL
SELECT 'body part without translation', body_part_code FROM dwh.dim_body_part
WHERE body_part_es IS NULL OR body_part_es = body_part_desc
UNION ALL
SELECT 'mine status or type not translated', mine_id FROM dwh.dim_mine
WHERE mine_status_es IN (N'Active', N'Abandoned', N'NonProducing') OR mine_type_es IN (N'Surface', N'Underground', N'Facility')
UNION ALL
SELECT 'violation profile not translated', CONCAT(negligence, '/', likelihood, '/', expected_injury)
FROM dwh.dim_violation_profile
WHERE negligence_es = negligence OR likelihood_es = likelihood OR citation_type_es = citation_type
   OR (expected_injury_es = expected_injury AND expected_injury <> N'Fatal');
