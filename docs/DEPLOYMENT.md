# Deployment Guide

Deploying to a real server, using the production-shaped stack from
Milestone 17/18 (`docker/docker-compose.prod.yml`). For running this on
your own machine for development instead, see
[`INSTALLATION.md`](./INSTALLATION.md).

## Topology

```
Internet ──▶ frontend (nginx, :8080→published port)
                 │  reverse-proxies /api/ and /static/
                 ▼
              backend (FastAPI, internal only)
                 │            │
                 ▼            ▼
         db (Postgres)   redis (cache)
      internal only         internal only
```

The frontend's nginx is the **only** container that publishes a port to the
host — `db`, `redis`, and `backend` are reachable only on the compose
network. The browser calls its own origin for everything (`VITE_API_BASE_URL`
is baked in as the relative path `/api/v1` at build time), so there is no
CORS to configure in production, and Postgres/Redis are never directly
reachable from the internet. See `ARCHITECTURE.md` section 7 for the full
reasoning.

**This stack does not terminate TLS.** Put a reverse proxy or load balancer
in front of it (a managed load balancer, Caddy, Traefik, or nginx again)
that terminates HTTPS and forwards plain HTTP to the `frontend` container's
published port. Terminating TLS a second time inside this stack would be
redundant infrastructure for no benefit — one edge is enough.

## Prerequisites

- A host with Docker and Docker Compose installed.
- A TLS-terminating reverse proxy or load balancer in front of it (see
  above) if this is reachable from the public internet.
- Nothing else — Postgres, Redis, and both application images are built and
  run by the compose file itself.

## Configuration

```bash
cd docker
cp .env.example .env
```

Edit `.env`. Two variables have **no default and compose refuses to start
without them** (`${VAR:?message}` syntax in `docker-compose.prod.yml`):

| Variable | How to generate |
|---|---|
| `POSTGRES_PASSWORD` | Any strong password — this is a private, internal-only database, but it's still the credential protecting all business data. |
| `SECRET_KEY` | `openssl rand -hex 32`. Signs every JWT; anyone who has it can forge access tokens for any account. |

Everything else has a safe default (`POSTGRES_USER`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
`CORS_ORIGINS` empty, `FRONTEND_PORT=80`) — see `docker/.env.example` for the
full list and `INSTALLATION.md`'s environment variable reference for what
each one does.

## Deploying

```bash
cd docker
docker compose -f docker-compose.prod.yml up --build -d
```

This builds both production images (backend's `runtime` stage, frontend's
`prod` stage — the same images CI's `docker-build` job already verified
build successfully) and starts all four services in the background.
`restart: unless-stopped` is set on every service, so the stack survives a
host reboot without manual intervention.

### Running migrations

The backend image does **not** run migrations automatically on startup —
deliberately, so a bad migration fails a controlled, observable step rather
than crash-looping the application container. Run them explicitly, once,
after `db` is healthy:

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

Do this on first deploy, and again after pulling any change that adds a new
migration.

### Creating the first admin user

`scripts/create_superuser.py` lives at the repo root, outside the
`backend/` build context, so it isn't part of the built image (the backend
`Dockerfile`'s `COPY . .` only copies `backend/`). Copy it in and run it
once:

```bash
docker compose -f docker-compose.prod.yml cp ../scripts/create_superuser.py backend:/app/create_superuser.py
docker compose -f docker-compose.prod.yml exec backend python create_superuser.py \
  --email admin@example.com --full-name "Admin User"
```

## Health checks

- `frontend`: `wget` against `/` (its own `HEALTHCHECK` in the Dockerfile).
- `backend`: `/api/v1/health/live` (liveness only — never checks the
  database, so a slow/unreachable DB doesn't look like a crashed process
  and trigger unnecessary container restarts; see `app/api/v1/endpoints/health.py`).
  Point your load balancer's health check at `/api/v1/health/ready`
  instead (through the frontend's `/api/` proxy) if you want DB
  reachability reflected in routing decisions.
- `db`/`redis`: `pg_isready`/`redis-cli ping`, gating `depends_on:
  condition: service_healthy` for `backend`.

## Updating a deployment

```bash
git pull
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head  # if new migrations exist
```

Compose rebuilds and recreates only the containers whose image or config
actually changed.

## Backups

Postgres data lives in the named volume `postgres_data`; uploaded product
images and the trained forecasting model live in `backend_uploads` and
`backend_ml_artifacts`. At minimum, back up the Postgres volume regularly —
it's the only data that can't be regenerated:

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U "${POSTGRES_USER:-inventory}" "${POSTGRES_DB:-inventory}" > backup.sql
```

`backend_uploads` (product images) is worth backing up too if re-uploading
every image manually isn't acceptable; `backend_ml_artifacts` is safe to
skip — it's fully regenerated by `POST /forecasting/train`.

## Scaling notes

This is a single-instance deployment (one `backend`, one `frontend`
container each). It doesn't need to be more than that for this project's
scale, but if it ever did:

- `backend` is stateless (session state is a JWT, not server-side) and can
  be scaled horizontally behind the same nginx — no code change needed.
- Product image storage (`backend/app/core/storage.py`) is local disk by
  design (see `ARCHITECTURE.md` section 7) — running more than one backend
  replica would need it swapped for a shared object store (S3-compatible)
  first, since local disk isn't shared across containers.
- `db`/`redis` are both single instances with no replication configured —
  add that (managed Postgres, Redis with persistence/replication) before
  scaling matters more than backups.
