# ScoutIQ staging operations

Status: engineering through Step 50 is implemented and tested (449 backend and 25 frontend tests). Step 49 infrastructure is prepared; hosted deployment is deferred at the user's request. The hosting budget is free only. No paid resources have been created. Real beta recruitment and feedback remain launch activities after hosting is selected.

## Intended hosted layout

The React/TypeScript frontend builds a Cloudflare Worker through Sites. FastAPI and PostgreSQL stay separate and portable. Both components have Dockerfiles. A hosting provider and its free-tier limits will be selected later. No paid-provider configuration is selected in this repository.

The frontend runtime variable `SCOUTIQ_API_ORIGIN` must be the actual HTTPS backend origin, without credentials or a path. Until it is set, the interface identifies the pending data-service setup. The existing owner-private Site has not been deployed. Preserve its audience if used later.

## Provider-neutral rollout

1. Select a free plan and verify its account-specific limits. No paid upgrades, domains or additional resources are authorized. Keep the beta within included usage and stop if provisioning requires a paid change.
2. Publish only sanitized source without the original repository's unreviewed history. The legacy repository tracked local files. Exclude environment files, virtual environments, database dumps, node_modules, caches and credentials.
3. Provision a separate staging PostgreSQL database, preferably version 18. Confirm support for btree_gist, PL/pgSQL triggers and migrations. Keep database networking private or require TLS and explicit access rules. Never point staging at the existing development database.
4. Run `python ops/migrate.py` once with an owner-only `MIGRATION_DATABASE_URL`. It upgrades Alembic and checks schema drift and audit capture. Normal server startup does not run migrations.
5. Provision the non-owner scoutiq_runtime login through the provider's secret manager and apply runtime-grants.sql, adjusting the database name. DATABASE_URL for serving uses this login. Keep the owner URL only in the migration job.
6. Set ENVIRONMENT=staging, an independent random JWT_SECRET_KEY, explicit HTTPS ALLOWED_ORIGINS, and the actual API hostname in ALLOWED_HOSTS or PUBLIC_HOSTNAME. Include localhost for internal health checks. Access/refresh lifetimes are 15 minutes/30 days. Use provider HTTPS termination, HTTP-to-HTTPS redirects and certificate renewal. Trust forwarded headers only from verified ingress proxy addresses.
7. Run `python ops/deploy_check.py`, then confirm the public HTTPS /health/ready returns 200. Configure the frontend API origin, deploy it and verify HTTPS. Local .dev.vars is never deployed.
8. Smoke-test registration, login, refresh/reload, logout, viewer/admin isolation, private watchlists, and report history. Use licensed demonstration data or explicitly disposable software fixtures. Do not redistribute development records whose rights are unspecified.
9. Measure resource use and response times with representative licensed data. A free-tier beta has capacity constraints; no commercial capacity guarantee has been established.

## Local container integration sandbox

Install a working Docker Engine/Compose before running. Docker is not installed in this workstation session, so container build/start has not been verified locally. CI includes both Docker builds. Source typechecks, application tests and the Worker build run locally.

Copy `deploy/.env.example` to ignored `deploy/.env`. Generate a URL-safe random PostgreSQL password and an independent JWT secret (at least 32 characters). From the repository root:

```sh
docker compose --env-file deploy/.env config --quiet
docker compose --env-file deploy/.env up --build -d
```

This sandbox binds only `127.0.0.1:5173`, uses an isolated `scoutiq_staging` database/volume, and uses development cookie behavior for loopback HTTP. PostgreSQL and the API have no published ports. It never connects to the workstation's development database. The frontend container runs the built Worker in Wrangler's local runtime; hosted frontend serving uses Sites. This loopback sandbox is not the hosted HTTPS staging environment.

## Backups and restore drills

The backup tool reads `DATABASE_URL` and optional `RESTORE_DATABASE_URL` only from environment secrets. PostgreSQL credentials go to subprocess environment variables, never command arguments. PostgreSQL client tools must match or exceed the server major version.

```sh
python ops/database_backup.py --output /secure/backups
python ops/database_backup.py --output /secure/restore-drills --restore-into
```

For a drill, provision an empty separate database named `scoutiq_restore_*` and set its URL as `RESTORE_DATABASE_URL`. The tool refuses other names, the source target, or any target with existing public tables. It never issues DROP or `--clean`. It exports a single consistent snapshot for pg_dump and the verification manifest, restores in one transaction, and compares schema revision, key table counts and the original player fields' digest.

The final local drill on 16 November 2026 restored revision `20261116_0015`, all five original players and the original player-field digest `2d6813cfa010b2c54386ef40c278e67e4692e76c946b77713a63735bfea3536d` into a separate scratch database. Development records and their ID sequence remained unchanged.

Before beta, configure daily provider backups plus encrypted offsite retention, document who can restore, choose retention and recovery targets, and run an actual hosted restore drill. No offsite destination or schedule is active yet. Protect backups as private account and report data. Do not put dumps in Git or a public Site archive.

## Monitoring and incident response

The readiness health check tests the database and migration head. Configure external HTTPS checks for both the Site and API; alert on persistent readiness failures, 5xx increases, disk growth and backup age. `/admin/operations` provides per-process route-template counters and total duration. Counters reset on restart and are not a distributed monitoring backend.

Structured logs contain request IDs, method, route template, status and duration. They omit raw paths, queries, request bodies, credentials and traceback parameter dumps. The same request ID reaches the frontend API response. Restrict provider log access and retention.

For an incident: restrict staging access, inspect request IDs and readiness, confirm the schema revision and resource limits, then redeploy a known compatible application version. Prefer forward schema fixes; do not automatically downgrade a data-bearing migration. Restore only into a new isolated database, validate it, then approve a deliberate cutover. Changing JWT keys signs everyone out. Password changes revoke that user's active sessions.

## Deployment checks

`.github/workflows/verify.yml` runs backend regression/migration tests with disposable PostgreSQL, frontend tests/typechecking/build, and both Docker builds. It is prepared but has not run on a connected Git hosting service. Configure the chosen provider to deploy only the reviewed branch after these checks pass. Maintain separate production and staging databases, JWT secrets and Site runtime origins.

Primary references used: [Docker startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/), [PostgreSQL pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html).
