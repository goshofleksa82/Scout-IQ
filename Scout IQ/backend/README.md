# ScoutIQ backend

Engineering through Step 50 is implemented and verified with 449 backend tests.
Hosted deployment is deferred, and real-user beta activities remain pending.
See `../README-RUN.md` and `../deploy` for setup, operations and launch materials.
Public player analytics accompany authenticated private scouting work and
administrator-only data management.

Step 26 adds `/auth/refresh` and `/auth/logout`. Login keeps its existing JSON
response and sets a rotating HttpOnly refresh cookie scoped to `/auth`. Only a
SHA-256 digest of the random 384-bit refresh secret is stored in PostgreSQL.
Refreshes retain the original session's absolute expiration (30 days by default),
and reuse of a rotated token revokes its entire session family. Concurrent refresh
requests serialize on the user row. Use one in-flight refresh per browser session.
Logout revokes that family; existing access tokens expire normally. Access tokens
default to 15 minutes; an existing configured lifetime remains in effect.
`REFRESH_TOKEN_EXPIRE_DAYS` accepts 1–90. Cookies are Secure in production and
SameSite=Lax. Browser session requests reject origins outside the backend origin
and `ALLOWED_ORIGINS` (local Vite origins by default). Use `credentials: include`
when calling the API from the frontend; refresh secrets stay out of JavaScript.

Step 27 adds authenticated `PATCH /users/me` and
`POST /users/me/change-password` (`current_password`, `new_password`). Profile
updates accept only username/email; empty updates are no-ops, explicit nulls and
privilege fields are rejected, and duplicate identities return 409. Changing a
password requires the current password and revokes all refresh sessions and
existing access tokens through a database-backed token version. Login and
password changes serialize on the account row to prevent stale-password races.

Steps 28–29 add SQL pagination (`page`, `page_size`, maximum 100) to `GET /players`
and combined `GET /players/search`. List responses retain `players` and add
`total`, `page`, `page_size`, `total_pages`, `has_next`, and `has_previous`.
Search accepts a literal case-insensitive name substring, exact case-insensitive
club/position, min/max age/goals/assists/minutes, sorting, and pagination. Range
bounds are inclusive. SQL wildcards in names are treated literally. Numeric and
club/position indexes support filters; substring names currently use a scan
rather than requiring the pg_trgm extension. Legacy filter/sort routes retain
their existing contracts.

Step 30 organizes implementation under `app/api`, `app/models`, `app/schemas`,
`app/services`, `app/repositories`, and `app/core`. `app.main:create_app` composes
the application. The original module names remain compatibility imports that
share module identity, so existing imports, dependency overrides, and the
`uvicorn main:app` command keep working. Configuration is validated centrally;
authentication dependencies and sanitized database errors are shared.

Step 31 adds public club/competition listing, detail, and relationship endpoints,
with admin-only create/update/delete. Every player now has a required club foreign
key. Existing club strings remain a compatibility field, and legacy name-based
player writes resolve a structured club in the same transaction. Club renames
update that compatibility name. Countries not present in the original data remain
unknown (NULL). Referenced entities cannot be deleted. The migration backfills
club relationships without changing existing player names, totals, or IDs.

Step 32 adds seasons, dated player-club memberships, transfers, and historical
search. Memberships use half-open date intervals `[joined_on, left_on)`; a
PostgreSQL GiST exclusion constraint (btree_gist) prevents overlapping assignments
for the same player. The season identifies the joining season; memberships may
continue into later seasons until an actual departure is recorded. Transfers
close the previous open membership and update the current club atomically.
Existing players receive no invented joining dates. Historical search can filter
club, date, or an overlapping season. Once membership history exists, club changes
through legacy PATCH are rejected in favor of the transfer endpoint.

Step 33 adds match creation/retrieval, participant rosters, and goal/assist/card
events. Match dates are interpreted in UTC and must fall within their season.
Participants require a dated membership for one of the match's clubs; the system
does not assume today's club proves historical participation. Assists reference
a teammate's goal at the same timestamp. Scheduled matches cannot accept events.
Stats and events are separate evidence; legacy career totals are not overwritten.

Step 34 adds per-player match statistics (minutes, goals, assists, shots, passes,
tackles, progressive passes/carries), with unique player/match records and database
consistency checks. `/players/{id}/match-stats?season_id=...` aggregates finished
matches in PostgreSQL. It reports metric coverage, preserves missing values as
NULL, and distinguishes recorded matches from appearances with positive minutes.
Zero-minute records cannot contain playing actions. Events cannot exceed recorded
goal/assist totals, and totals cannot be reduced below recorded events. The
existing manually reported player totals remain available separately.

Step 35 adds admin-only CSV imports at `/imports/players`, `/imports/matches`,
and `/imports/player-stats` (UTF-8, 2 MiB/1000 rows maximum). Send `text/csv` with
`source`, `rights_basis`, and `rights_confirmed=true` query parameters. Every row
requires a stable `external_id` plus the corresponding create schema's required
fields. Match-stat rows also require `match_id`. Repeat imports with identical
source IDs are skipped; changed content is rejected rather than overwriting.
Validation or database conflicts roll back the entire football-data batch.
Import reports preserve source, declared rights, author, row errors, and counts.
Imported records link back to their batch. Match statistics require existing
participant rosters; importing a match does not invent its participants or events.

Step 36 exposes `/analytics/players/{id}/metrics?season_id=...`: goals, assists,
contributions, shots, tackles and completed passes per 90; pass completion and goal
conversion percentages; and progressive actions per 90 where both progressive
passes and carries are supplied. Missing inputs/zero denominators yield NULL.
Every metric includes its formula, recorded-match source and metric coverage.

Step 37 adds `/analytics/rankings` with position-specific metrics, minimum minutes,
season selection, and provider selection. Competition ranks share ties; mean-rank
percentiles span 0–100 with tied groups at their average position. A singleton has
no percentile. The published two-decimal metric determines ties. Blended provider
data require selection; `data_source` filters source records before aggregation.
Goalkeeper rankings describe distribution only because save/shot-quality data
are not collected. Rankings do not adjust for opposition or tactical context.

Step 38 adds `/analytics/players/{id}/similar` with position-specific default
features, optional feature selection, minimum minutes, season and provider. It
uses complete cases, population z-scores and RMS standardized distance, mapped to
`100 / (1 + distance)`. Constant dimensions contribute zero. Responses include
normalization parameters, feature values, a cohort fingerprint and limitations.
Missing values are never imputed, and insufficient samples return explicit states.

Step 39 adds `/analytics/players/{id}/trends`: minutes-weighted rolling metrics,
recent/previous windows, chronological observations and season-over-season change.
Missing matches are not interpolated. Exploratory change signals require at least
five complete appearances per window and a two-sided permutation comparison
(exact up to 5000 partitions, otherwise 2000 seeded draws), plus a material-effect
threshold. Their assumptions and limitations are included in the response.

Step 40 adds immutable scoring-model definitions, admin-created semantic versions,
and `/analytics/players/{id}/score`. The score is a weighted mean of peer-group
percentiles among complete cases from one season, position group and source.
At least three eligible players are required. Every component, weight, contribution,
criteria version, algorithm version and cohort fingerprint is returned. The highest
semantic model version is the default; `model_id` reproduces a chosen definition.
Missing required metrics prevent scores. Built-in 0.1.0 definitions are explicitly
uncalibrated statistical decision-support criteria, not validated player-quality
models. Goalkeeper definitions describe distribution only.

## Local setup

The current Windows environment is `C:\Scout-IQ\Scout IQ\.venv`. From this
backend directory:

```powershell
& '..\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
```

For an application-only installation use `requirements.txt`. The versions in
these files match the environment used to verify this implementation.

Keep database credentials and the JWT signing key in `.env` or environment
variables. `.env.example` provides the variable names with placeholders. Supply
your own PostgreSQL credentials and a separate, disposable `scoutiq_test`
database. URL-encode special characters in database usernames/passwords.

Generate a signing key locally and put it in `JWT_SECRET_KEY`:

```powershell
& '..\.venv\Scripts\python.exe' -c "import secrets; print(secrets.token_urlsafe(48))"
```

The application accepts only `HS256`, requires a signing key of at least 32
characters, and validates that the token lifetime is between 1 and 60 minutes
(default 15). Existing real environment values take precedence over `.env`.
Changing the signing key invalidates existing tokens.

Use [the migration instructions](migrations/README.md) when initializing a new
database or adopting an existing player database. The current development
database is already at `20261116_0002`; do not repeat its baseline adoption.
Authentication requires no additional schema migration after that revision.

Start the API:

```powershell
& '..\.venv\Scripts\python.exe' -m uvicorn main:app --reload --port 8001
```

Open <http://127.0.0.1:8001/docs>. This installation's PostgreSQL connection uses
port 8000, so the API example uses port 8001.

## Create an administrator

Run the trusted CLI from a terminal that supports hidden password prompts:

```powershell
& '..\.venv\Scripts\python.exe' create_admin.py --username scout_admin --email you@example.com
```

Choose your real username and email in the command, then enter and confirm your
own password. Passwords are never command-line arguments. The command validates
the same identity/password rules as registration, hashes the password, and
explicitly assigns the admin role. It refuses existing usernames/emails, including
existing viewers, and does not silently promote them. It also refuses an echoed
password-prompt fallback. Failed database writes roll back with a sanitized error.

The feature was tested with disposable accounts in `scoutiq_test`; no real admin
account or password was invented in the development database.

## Authentication API

### `POST /auth/register`

Send JSON containing `username`, `email`, and `password`. A successful request
returns HTTP 201 with `id`, `username`, `email`, `role`, and `is_active`.

* Usernames are trimmed, lowercased, 3–50 characters, and limited to ASCII
  letters, numbers, and underscores.
* Emails are validated, normalized to lowercase, and limited to 255 characters.
* Passwords are 12–128 characters and cannot consist only of whitespace.
  Meaningful spaces are preserved. Password values are protected in schema
  representations and stripped from validation error responses.
* Every public registration creates an active viewer. Supplying `role`,
  `is_active`, `hashed_password`, or other extra fields returns HTTP 422.
* A duplicate username or email returns HTTP 409, including a concurrent
  duplicate caught by the database's unique indexes.

### `POST /auth/login`

Send JSON with `username` and `password`. Success returns HTTP 200 with
`access_token` and `token_type: "bearer"`. Invalid credentials or an inactive
account return HTTP 401 with a Bearer challenge. Responses containing tokens
have `Cache-Control: no-store` and `Pragma: no-cache`.

### `GET /auth/me`

Send `Authorization: Bearer <access_token>`. The response exposes only the
current user's public fields; password hashes never appear in API responses.

Tokens are signature-checked using the configured algorithm and require `sub`,
`exp`, `iat`, `nbf`, and `type`. Dates must be integers; the subject must identify
a valid positive PostgreSQL integer ID; the type must be `access`. Missing,
malformed, tampered, unsigned, expired, or not-yet-valid tokens return HTTP 401.
Unknown or inactive users are also rejected. Permissions are read from the
database on every request, so disabling/demoting a user affects existing tokens.

## Player authorization

| Operation | Anonymous | Viewer | Admin |
| --- | --- | --- | --- |
| Player retrieval, filters, sorting, comparisons, rankings, statistics | Allowed | Allowed | Allowed |
| `POST /players` | 401 | 403 | Allowed |
| `PATCH /players/{player_id}` | 401 | 403 | Allowed |
| `DELETE /players/{player_id}` | 401 | 403 | Allowed |

The existing player validation, response formats, transaction rollbacks, and
sanitized database errors are preserved.

## Tests

```powershell
& '..\.venv\Scripts\python.exe' -m pytest -q
& '..\.venv\Scripts\python.exe' -m alembic current
& '..\.venv\Scripts\python.exe' -m alembic check
```

Tests validate the configured and live database name before creating/dropping
tables, require `scoutiq_test`, and explicitly block connections through the
development engine. They use an ephemeral signing key, dependency overrides,
and authenticated admin fixtures. Database failure tests isolate their faulting
sessions from authorization, while separate permission tests exercise real JWTs.
Migration rehearsals run in disposable test schemas. The previous read-only
development smoke script is now an isolated pytest test.

## References

The implementation uses [FastAPI's documented JWT/password approach](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[pwdlib for password hashing](https://frankie567.github.io/pwdlib/reference/pwdlib/),
and [PyJWT's explicitly configured signature and claim validation](https://pyjwt.readthedocs.io/en/stable/api.html).
