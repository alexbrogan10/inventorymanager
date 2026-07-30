# Backend

FastAPI service for the AI Inventory Management System. See
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for the layered
architecture this code follows.

## Local development (without Docker)

Requires Python 3.13 and a running PostgreSQL instance (or use
`docker compose -f ../docker/docker-compose.yml up db`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env   # then edit DATABASE_URL if needed

uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive docs (Swagger UI): http://localhost:8000/docs
- Health checks: `/api/v1/health/live`, `/api/v1/health/ready`

## Running migrations

```bash
alembic upgrade head                     # apply migrations
alembic revision --autogenerate -m "..."  # generate a new migration from model changes
```

## Testing

```bash
pytest
```

Tests run against `TEST_DATABASE_URL` (a separate database from the one the
app uses in dev - see docs/ARCHITECTURE.md's testing strategy), so it must
exist first: `createdb inventory_test` (or `CREATE DATABASE inventory_test;`
via `psql`). `pyproject.toml` enables coverage reporting by default (`--cov=app`).

## Linting & formatting

```bash
ruff check .        # lint
ruff format .        # format
mypy app tests       # type-check
```

## Creating an admin account

Public registration (`POST /api/v1/auth/register`) can only create EMPLOYEE
accounts. To bootstrap the first admin in a fresh environment:

```bash
python ../scripts/create_superuser.py --email admin@example.com --full-name "Admin User"
```
