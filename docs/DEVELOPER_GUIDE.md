# Developer Guide

How to work in this codebase day to day. For *why* it's shaped this way,
see [`ARCHITECTURE.md`](./ARCHITECTURE.md); for getting a copy running at
all, see [`INSTALLATION.md`](./INSTALLATION.md).

## Repo layout

```
inventorymanager/
├── backend/     # FastAPI app: app/{api,core,models,repositories,schemas,services,ml}
├── frontend/    # React SPA: src/{features,components,context,api}
├── database/    # ER diagram + reference SQL schema (docs, not code)
├── docker/      # docker-compose.yml (dev) and docker-compose.prod.yml
├── docs/        # This guide, architecture, roadmap, API/installation/deployment docs
├── scripts/     # Developer convenience scripts (e.g. create_superuser.py)
├── sample_data/ # Sample CSVs for the product import feature
├── powerbi/     # Power BI-ready export templates
└── tests/       # Reserved for cross-service end-to-end tests (empty for now)
```

Backend layering (strict one-way dependency: `api → services → repositories
→ models`, `core` depended on by everyone but depending on nothing):

- `models/` — SQLAlchemy ORM classes, one file per table.
- `repositories/` — all raw SQL/ORM querying, one per aggregate root. Never
  contains business rules.
- `services/` — business logic and validation, orchestrates one or more
  repositories. Raises domain-specific exceptions (`ProductNotFoundError`,
  `DuplicateSkuError`, ...) — never `HTTPException`, so services stay usable
  outside an HTTP context (tests, scripts, a future background worker).
- `schemas/` — Pydantic request/response models, kept separate from ORM
  models (see `ARCHITECTURE.md` section 2) so an API contract can differ
  from the DB shape without leaking DB internals.
- `api/v1/endpoints/` — thin: parses the request, calls one service method,
  translates domain exceptions to HTTP status codes. No business logic
  lives here.
- `core/` — config, DB session, security (JWT/bcrypt), cache, storage,
  export helpers. No upward imports from any of the layers above.

Frontend layering: `src/features/<name>/` is a vertical slice
(`api.ts`, `types.ts`, page/dialog components, colocated `*.test.ts(x)`);
`src/components/` holds cross-feature shared components (layout, nav,
loading/empty states); `src/context/` holds app-wide React context
(auth, notifications, theme).

## Adding a new feature (the vertical-slice pattern)

Every feature in this system (Suppliers, Products, Purchase Orders, ...) was
built the same way — follow this order for a new one:

**Backend:**
1. `models/<entity>.py` — SQLAlchemy model, registered in `models/__init__.py`.
2. `alembic revision --autogenerate -m "add <entity>"` — review the
   generated migration before running it; autogenerate is a good first
   draft, not always a correct one (it won't detect a renamed column, for
   instance).
3. `alembic upgrade head` — apply it locally.
4. `repositories/<entity>_repository.py` — CRUD + any custom queries.
5. `services/<entity>_service.py` — validation, domain exceptions.
6. `schemas/<entity>.py` — `<Entity>Create`, `<Entity>Read`, `<Entity>Update`.
7. `api/v1/endpoints/<entity>.py` — routes, wired into `api/v1/router.py`.
   Reads only need `Depends(get_current_user)`; writes need
   `Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))` (see
   `api/deps.py`) unless there's a specific reason to diverge (see
   `API.md`'s RBAC table for the one exception that exists today).
8. Tests in `backend/tests/test_<entity>.py`, against a real Postgres
   database (see [Testing](#testing) below) — not mocks.

**Frontend:**
9. `features/<entity>/types.ts` + `api.ts` (thin wrapper over the shared
   `apiClient`), with `api.test.ts` asserting the exact method/URL/params it
   sends.
10. Page/dialog components, colocated `*.test.tsx` using React Testing
    Library — mock `api.ts`, not `apiClient` directly, so tests exercise the
    same seam a real page does.
11. Add the route to the router and a nav entry if the feature has its own
    page.

**Docs:** update `docs/ARCHITECTURE.md` with a short "Milestone N" section
explaining any non-obvious design decision, and `docs/ROADMAP.md` to mark
the milestone done.

## Testing

```bash
# Backend (from backend/, virtualenv active)
pytest                    # full suite, against TEST_DATABASE_URL
pytest tests/test_x.py -v # one file

# Frontend (from frontend/)
npm run test              # once
npm run test:watch        # watch mode
npm run test:coverage     # with coverage report
```

Backend tests run against a **real PostgreSQL database**, not SQLite or
mocks — Postgres-specific behavior (enums, constraints, `ON DELETE` rules)
needs to be exercised faithfully. `TEST_DATABASE_URL` must point at a
database that exists (`createdb inventory_test`); the schema is
dropped/recreated once per test session and each test runs inside a
transaction rolled back afterward, so tests never see each other's data.
Redis-backed cache tests use `TEST_REDIS_URL` (a separate logical DB) the
same way. See `ARCHITECTURE.md` section 6 for the full rationale.

Frontend tests are colocated (`Component.test.tsx` next to `Component.tsx`)
and use React Testing Library + Vitest; every `features/*/api.ts` has a
matching `api.test.ts` that asserts request shape without a real network
call.

## Linting, formatting, type-checking

Run the **exact** commands CI runs before pushing — a subset that passes
locally can still fail CI if it happens to skip a check:

```bash
# Backend
ruff check .          # lint
ruff format --check . # format (ruff format . to fix)
mypy app tests        # type-check

# Frontend
npm run lint           # oxlint
npm run format:check   # prettier --check (npm run format to fix)
```

## Migrations

```bash
alembic revision --autogenerate -m "description"  # generate from model changes
alembic upgrade head                               # apply
alembic downgrade -1                               # roll back one revision
```

Always review an autogenerated migration by eye before running it — it's a
diff against the current DB schema, not a guarantee of correctness (renames,
data migrations, and some constraint changes need manual editing).

## CI

`.github/workflows/ci.yml` runs on every push/PR to `main`, as three jobs:
`backend` (lint → format → type-check → test, against real `postgres` and
`redis` service containers), `frontend` (lint → format → test → build), and
`docker-build` (actually builds both services' production Docker images —
gated on the first two passing, so a broken PR fails fast rather than
waiting on an image build). See `ARCHITECTURE.md` section 6 for why each
piece exists.

## Conventions

- **Branching**: this project was built milestone-by-milestone on a single
  long-lived feature branch, fast-forward-merged into `main` after each
  milestone's verification passed. A team working on multiple features in
  parallel would instead use one short-lived branch per feature/PR — the
  vertical-slice pattern above works the same either way.
- **Commits**: describe *why*, not *what* — the diff already shows what
  changed; the message should explain the reasoning a diff can't (see this
  repo's own history for examples).
- **No commented-out code, no TODOs left in merged code** — either finish
  it, delete it, or track it in `docs/ROADMAP.md`'s future-work section.
