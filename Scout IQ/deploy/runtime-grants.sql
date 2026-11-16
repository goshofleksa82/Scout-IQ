-- Run as the database owner after all migrations. Provision the LOGIN role and
-- password through the provider's secret manager, never this tracked file.
-- Runtime DATABASE_URL uses scoutiq_runtime; migration DATABASE_URL uses owner.
GRANT CONNECT ON DATABASE scoutiq_staging TO scoutiq_runtime;
GRANT USAGE ON SCHEMA public TO scoutiq_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO scoutiq_runtime;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO scoutiq_runtime;
REVOKE UPDATE,DELETE,TRUNCATE ON audit_logs FROM scoutiq_runtime;
REVOKE UPDATE,DELETE,TRUNCATE ON scouting_report_versions,scoring_models FROM scoutiq_runtime;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON alembic_version FROM scoutiq_runtime;
REVOKE CREATE ON SCHEMA public FROM scoutiq_runtime;
-- Reapply after schema upgrades; never grant DDL or table ownership to runtime.
