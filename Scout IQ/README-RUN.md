# ScoutIQ — run and verify

The engineering work for roadmap Steps 26–50 is implemented. Hosted staging and real-user beta activities remain pending; hosting selection is deferred. This checkout has a FastAPI/PostgreSQL backend and React/TypeScript frontend. See `deploy/OPERATIONS.md` for rollout and `deploy/BETA-LAUNCH.md` for the focused beta plan.

## Local development

Verified with Python 3.13, Node 22.20 and PostgreSQL 18. The existing Windows checkout is `C:\Scout-IQ\Scout IQ`. Its active Python environment is the root `.venv`, not `backend/.venv`. PostgreSQL runs on port **8000**; FastAPI uses **8001**, and the frontend **5173**.

For a new checkout, create a root Python virtual environment and install `backend/requirements-dev.txt`. Copy `backend/.env.example` to ignored `backend/.env`, set independent PostgreSQL application/test URLs and a random JWT signing secret. The test database must be named `scoutiq_test` and must be disposable. The application database must be separate. Provision the PostgreSQL `btree_gist` extension through the database owner where required.

Back up an existing database before upgrades. In the existing checkout, revision `20261116_0015` is already applied; do not reset or reseed it. In a new target, run `python ops/migrate.py` from `backend` with the migration-owner environment configured. Normal server startup does not migrate the database.

From `backend`, start the API:

```powershell
& '..\.venv\Scripts\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 8001
```

In `frontend`, run `npm ci` when dependencies are absent. Copy `.dev.vars.example` to ignored `.dev.vars`, using `SCOUTIQ_API_ORIGIN=http://127.0.0.1:8001`. Start the interface:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. API documentation is at `http://127.0.0.1:8001/docs`; readiness is `/health/ready`. No administrator password is bundled. To create an administrator, run `python ops/create_admin.py --username YOUR_NAME --email YOUR_EMAIL` in the backend; the password is entered twice through a hidden terminal prompt. Existing users are never promoted by this command. Self-registration always creates a viewer. The existing development database still contains its original five players and no real user accounts.

## Verification

From `backend`, run `..\.venv\Scripts\python.exe -m pytest -q`. The final regression result is **449 passed** against the isolated PostgreSQL test database. From `frontend`, run `npm run typecheck`, `npm test` and `npm run build`: **25 frontend tests pass**, and the Worker production build succeeds. Local browser checks cover desktop/mobile discovery, profiles, comparisons, authentication, private watchlists, report history, admin quality review, onboarding and beta feedback.

The CI workflow and both Dockerfiles are prepared. Docker is not installed on the verified workstation, so container execution has not been verified here. The Compose setup is a loopback integration sandbox, not hosted HTTPS staging.

## Licensed demonstration data

`backend/demo` contains an attributed CC BY 4.0 subset of the Pappalardo et al. football dataset: 42 historical players, 13 matches and 195 appearance records for France/Croatia at the 2018 World Cup. Ages are as of 15 July 2018; national teams are not current clubs. Unknown tackles/progressive actions stay missing. See the demo README, manifest and `/data-notes` for definitions, rights and limitations.

The demo loader only accepts a new, separate `scoutiq_demo*` database, requires an existing operator account and refuses targets with football data. It does not load on startup and has not changed the original development records. Never replace the existing database to obtain a demonstration.

## Before external beta

Choose a free hosting provider, execute container/hosted CI checks, configure HTTPS and isolated credentials, schedule backup/expiry jobs and alerts, and verify a hosted restore. Finalize operator identity/contact and privacy/terms requirements. Recruit actual testers and collect actual feedback; the empty trackers and invitation draft are preparation only. No external tester messages have been sent.

Publish only the sanitized source package or reviewed current files. The original parent Git history includes legacy local files and must not be pushed without a separate history/secrets review.
