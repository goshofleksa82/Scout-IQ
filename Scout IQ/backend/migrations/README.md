# ScoutIQ migrations — Step 25.1

Run commands from `C:\Scout-IQ\Scout IQ\backend` with the existing Windows
interpreter `..\.venv\Scripts\python.exe`. The other virtual environment at
`backend\.venv` is the legacy environment and is not used for this work.

Alembic is already installed in the Windows environment. For another existing
ScoutIQ application environment, install `requirements-migrations.txt`.

`env.py` reads `DATABASE_URL` from the environment or `backend/.env`, imports
`models.Base.metadata`, and never imports the API or authentication modules.
The connection string is not stored in `alembic.ini`. Environment values take
precedence over `.env` values.

## Revision history

* `20261116_0001`: the existing players schema, including its identity ID and
  three nonnegative statistics constraints. Existing verified installations
  **stamp** this revision; only empty databases run its upgrade.
* `20261116_0002`: adds users, generated IDs, unique username/email indexes,
  required columns, database defaults (`viewer`, `true`), and a database check
  limiting roles to `viewer` and `admin`. It does not touch players or their ID
  sequence. Downgrading to `20261116_0001` removes users and their data only.

Downgrading below the players baseline deliberately raises an error so a routine
Alembic rollback cannot delete the pre-existing player table.

## Adopting an existing database

Do not blindly run `upgrade head` on a database without migration history.
First inspect the actual schema, verify it matches the baseline, verify the
players ID sequence is synchronized, and retain a database backup appropriate to
the environment. If users or Alembic history already exist, inspect them before
choosing a migration path; do not stamp `head` to hide schema differences.

For the inspected ScoutIQ database, there was one `players` table with five
players, identity IDs, and the three statistics checks; users and Alembic history
were absent. The sequence last value was 6, equal to the highest player ID.

After verifying the target and explaining the change, adopt the baseline and
upgrade using one transaction (the one-time adoption should not be rerun on
an already versioned installation):

```python
from pathlib import Path
from alembic import command
from alembic.config import Config
from database import engine

config = Config(str(Path("alembic.ini").resolve()))
with engine.begin() as connection:
    config.attributes["connection"] = connection
    command.stamp(config, "20261116_0001")
    command.upgrade(config, "head")
```

The baseline is recorded rather than executed, so the existing player table,
records, constraints, and sequence remain in place. Review the users SQL without
connecting or changing data:

```powershell
& '..\.venv\Scripts\python.exe' -m alembic upgrade '20261116_0001:head' --sql
```

For a **new empty** database, point `DATABASE_URL` at that database, then run:

```powershell
& '..\.venv\Scripts\python.exe' -m alembic upgrade head
```

## Routine verification

```powershell
& '..\.venv\Scripts\python.exe' -m alembic current
& '..\.venv\Scripts\python.exe' -m alembic check
& '..\.venv\Scripts\python.exe' -m pytest -q
```

`alembic check` compares modeled columns, types, defaults, and indexes. Continue
to inspect check constraints manually; autogeneration is not a complete schema
audit. [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

All tests that create or drop tables use the separate `scoutiq_test` database.
Migration tests additionally use temporary schemas that are rolled back after
each test. Tests cover a fresh database, adopting populated players, users-only
rollback, defaults, constraints, sequence preservation, and schema drift.

## History and follow-up completion

The pre-change regression baseline was **140 passing tests**, rather than the
134 in the handoff. Auth schemas, Argon2 hashing, JWT utilities and auth routes
already existed. At Step 25.1, `require_admin` was not attached to player write
routes, and `create_admin.py` and `test_auth.py` were empty. The subsequent
Step 25.2–25.6 implementation completed and tested those features. See the
backend README for the current authentication and admin setup instructions.

The former `test_models.py` smoke script queried development during collection.
It has since been converted to an isolated pytest test. Model tests use only
the test database, and test connections through the development engine are
explicitly blocked.

The repository already tracks `.env` and legacy virtual-environment/cache files.
The new `.gitignore` prevents new untracked copies from being added, but does not
untrack existing files or rewrite history. Review that before publishing code.

Database defaults are declared in addition to ORM defaults so direct SQL inserts
also receive them. [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/21/core/defaults.html#server-invoked-ddl-explicit-default-expressions)
