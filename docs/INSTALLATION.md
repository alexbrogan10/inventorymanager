# Installation Guide

Two ways to run this locally: Docker Compose (one command, nothing else to
install) or a manual setup (each service run natively, useful when you want
to attach a debugger or iterate on one service without rebuilding a
container). Both end up at the same place. For deploying to a real server
instead of your own machine, see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

## Option A: Docker Compose (recommended)

**Prerequisites:** Docker and Docker Compose.

```bash
git clone <this-repo-url> && cd inventorymanager
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose -f docker/docker-compose.yml up --build
```

This starts four containers: `db` (Postgres 16), `redis` (Redis 7),
`backend` (FastAPI with `--reload`), and `frontend` (Vite dev server). The
defaults in `backend/.env.example`/`frontend/.env.example` already point at
the compose service names (`db`, `redis`), so no editing is required for a
first run.

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (interactive docs at `/docs` — see
  [`API.md`](./API.md))

Once it's up, create the first admin account (needed to log in — see
[Creating the first user](#creating-the-first-user) below), then skip ahead
to [Verifying the stack](#verifying-the-stack).

To stop: `Ctrl-C`, then `docker compose -f docker/docker-compose.yml down`
(add `-v` to also drop the Postgres volume and start from a clean database
next time).

## Option B: Manual setup (no Docker)

**Prerequisites:**

| | Version | Used for |
|---|---|---|
| Python | 3.13 | Backend |
| Node.js | 22 | Frontend |
| PostgreSQL | 16 | Primary database |
| Redis | 7 | Dashboard summary cache (optional — see below) |

### 1. Database

Create the dev and test databases (matching `backend/.env.example`'s
defaults — adjust if you use different credentials):

```sql
CREATE USER inventory WITH PASSWORD 'inventory';
CREATE DATABASE inventory OWNER inventory;
CREATE DATABASE inventory_test OWNER inventory;
```

### 2. Redis (optional)

Redis backs one thing: caching `GET /dashboard/summary`. The app degrades
gracefully if it's unreachable (a cache miss every time, never an error —
see `backend/app/core/cache.py`), so it's fine to skip this for local
development. If you want it:

```bash
redis-server --daemonize yes --port 6379
```

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env   # edit DATABASE_URL/REDIS_URL if you used different values above

alembic upgrade head
uvicorn app.main:app --reload
```

- API: http://localhost:8000 (interactive docs at `/docs`, health checks at
  `/api/v1/health/live` and `/api/v1/health/ready`)

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env   # edit VITE_API_BASE_URL if the backend isn't on localhost:8000
npm run dev
```

- App: http://localhost:5173

### Creating the first user

Public self-registration (`POST /auth/register`, or the frontend's Register
page) can only ever create an `employee` account — see
[`API.md`](./API.md#roles-rbac) for why. To create the first
`admin` account, use the bootstrap script (works against either setup
above, as long as the backend's virtualenv can reach whatever
`DATABASE_URL` is configured):

```bash
cd backend && source .venv/bin/activate && cd ..
python scripts/create_superuser.py --email admin@example.com --full-name "Admin User"
```

You'll be prompted for a password interactively (never passed as a CLI
argument, so it never ends up in shell history).

### Verifying the stack

1. `curl http://localhost:8000/api/v1/health/ready` → `{"status": "ok"}`
   confirms the backend can reach Postgres (a `503` means it can't).
2. Open http://localhost:5173, log in with the admin account created above.
3. Create a category, a supplier, then a product referencing both — if all
   three save and the product list shows the new row, the full
   frontend → backend → Postgres path works end to end.
4. Open http://localhost:8000/docs and try `GET /dashboard/summary` with
   the "Authorize" button — if Redis is running, a second identical request
   within 30 seconds should be noticeably faster (served from cache).

## Environment variable reference

### `backend/.env` (see `backend/.env.example`)

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Informational; doesn't gate behavior today. |
| `DEBUG` | `true` | Passed to FastAPI's `debug=`. |
| `DATABASE_URL` | `postgresql+psycopg://inventory:inventory@localhost:5432/inventory` | Primary connection string. |
| `TEST_DATABASE_URL` | `...inventory_test` | A separate database — the test suite drops/recreates its schema every run. |
| `SECRET_KEY` | *(insecure dev default)* | JWT signing key. **Must** be overridden with `openssl rand -hex 32` outside local dev. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated. Irrelevant in production, where nginx reverse-proxies same-origin — see `DEPLOYMENT.md`. |
| `UPLOAD_DIR` | `uploads` | Where product images are written; served at `/static`. |
| `ML_MODEL_DIR` | `ml_artifacts` | Where the trained demand-forecasting model is persisted. |
| `REDIS_URL` | `redis://localhost:6379/0` | Dashboard cache. Unreachable Redis degrades gracefully — never a hard dependency. |
| `TEST_REDIS_URL` | `redis://localhost:6379/1` | Separate logical DB so test cache flushes never touch dev data. |
| `DASHBOARD_CACHE_TTL_SECONDS` | `30` | How long a cached dashboard summary is served before recomputing. |

### `frontend/.env` (see `frontend/.env.example`)

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Baked in at Vite build time. In production this is set to the relative path `/api/v1` instead — see `DEPLOYMENT.md`. |

### `docker/.env` (production compose only — see `docker/.env.example`)

Local dev's `docker-compose.yml` hardcodes non-secret dev credentials
directly, so this file is only needed for `docker-compose.prod.yml`. Covered
in [`DEPLOYMENT.md`](./DEPLOYMENT.md#configuration).

## Troubleshooting

- **`connection refused` to Postgres**: confirm it's actually running
  (`pg_isready -h localhost -p 5432`) and that `DATABASE_URL`'s host/port
  match where it's listening.
- **`alembic upgrade head` fails with "database does not exist"**: you
  skipped step 1 above — create `inventory` (and `inventory_test`, for
  running tests) first.
- **Frontend loads but every request 401s**: check `VITE_API_BASE_URL`
  actually points at the running backend, and that you're logged in (the
  token is stored client-side and expires after `ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Dashboard works but never seems cached**: Redis isn't required, so
  check `redis-cli ping` returns `PONG` before assuming something's broken
  — a missing Redis is silent by design.
