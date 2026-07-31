# Architecture Overview

This document explains the system design of the AI Inventory Management System and
the reasoning behind each major decision. It is a living document — it will be
extended as later milestones introduce new subsystems (ML pipeline, notifications,
caching, etc.).

## 1. System Context

```
                         ┌─────────────────────┐
                         │        Users         │
                         │ (Admin / Manager /    │
                         │      Employee)        │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │   React SPA (Vite)   │
                         │  TypeScript + MUI    │
                         └──────────┬───────────┘
                                    │ REST (JSON) / JWT
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI Backend    │
                         │  (Uvicorn / ASGI)    │
                         └──────────┬───────────┘
                       ┌────────────┼─────────────┐
                       ▼            ▼              ▼
                ┌───────────┐ ┌───────────┐ ┌─────────────┐
                │ PostgreSQL │ │  Redis    │ │  ML Layer    │
                │ (system of │ │ (cache /  │ │ (scikit-learn│
                │  record)   │ │ sessions, │ │  forecasting)│
                │            │ │  later)   │ │              │
                └───────────┘ └───────────┘ └─────────────┘
```

The frontend never talks to Postgres, Redis, or the ML layer directly — everything
goes through the FastAPI REST API. This keeps a single, auditable entry point for
business rules and security.

## 2. Backend: Layered Architecture

The backend follows a strict **layered architecture** so that business logic never
leaks into HTTP handling code, and persistence details never leak into business
logic. This is what makes the Repository Pattern / Service Layer / SOLID
requirements concrete rather than decorative.

```
app/
├── api/            # Layer 1: HTTP interface (FastAPI routers)
├── schemas/         # Pydantic request/response models (the API's public contract)
├── services/        # Layer 2: business logic / use cases
├── repositories/     # Layer 3: data access abstraction
├── models/           # Layer 4: SQLAlchemy ORM models (the persistence schema)
└── core/             # Cross-cutting: config, DB session, security, dependencies
```

**Request flow:** `router → schema (validate) → service (business rules) →
repository (persistence) → model (table) → database`

| Layer | Responsibility | Depends on | Must NOT do |
|---|---|---|---|
| `api/` (routers) | Parse HTTP request, call a service, map result to HTTP response/status code | `schemas`, `services` | Contain business rules or raw SQL |
| `schemas/` | Define and validate the shapes that cross the API boundary (input & output) | Pydantic only | Reference ORM models directly (kept separate so the DB schema can evolve independently of the API contract) |
| `services/` | Orchestrate one business use case (e.g. "receive a purchase order and increment stock") | `repositories` (via abstract interfaces) | Import SQLAlchemy or FastAPI |
| `repositories/` | Translate business objects to/from persistence queries | `models`, DB session | Contain business rules |
| `models/` | Define tables, relationships, constraints, indexes | SQLAlchemy only | — |
| `core/` | Settings, DB engine/session factory, security (JWT/bcrypt), reusable `Depends()` providers | — | — |

### Why this shape (SOLID in practice)

- **Single Responsibility** — each layer has exactly one reason to change (a new
  validation rule touches `schemas/`; a new business rule touches `services/`; a
  new query touches `repositories/`).
- **Dependency Inversion** — services depend on repository *abstractions*
  (Python `Protocol`/ABC interfaces), not concrete SQLAlchemy calls. This is what
  makes services unit-testable with in-memory fakes instead of a real database.
- **Open/Closed** — new repository implementations (e.g. a caching decorator, or
  swapping Postgres for another store in a single aggregate) can be introduced
  without touching services.
- **Dependency Injection** — FastAPI's `Depends()` is used throughout to inject the
  DB session, the current authenticated user, and service instances into route
  handlers. This is FastAPI's native DI mechanism, so we lean on it rather than
  building a custom container.

### Why Pydantic schemas are separate from ORM models

Returning ORM models directly from an API is a common anti-pattern: it leaks
internal columns (password hashes, soft-delete flags), makes API versioning
impossible, and couples your DB migrations to your API contract. `schemas/`
defines exactly what a client can send and receive; `models/` defines exactly
what is stored. A `ProductRead` schema and a `Product` ORM model can diverge
freely as the app grows (e.g. adding a computed `stock_status` field to the
response without a matching DB column).

## 3. Database

- **PostgreSQL** as the single system of record — chosen over MySQL/SQLite for
  its strong support of constraints, enums, JSONB (useful later for flexible
  metadata such as ML feature snapshots), and its maturity in production
  deployments.
- **SQLAlchemy 2.0-style ORM** (typed declarative models) for the persistence
  layer.
- **Alembic** for migrations. Migrations live in `backend/alembic/` (next to the
  models that generate them) because they are a backend build artifact, not
  documentation.
- The top-level `database/` directory is **not** where migrations live. It holds
  human-facing database documentation: the ER diagram, a plain-SQL reference
  schema for onboarding/reading without running the app, and seed data
  definitions. Keeping this separate from `backend/alembic/versions/` avoids
  confusing "the history of schema changes" (Alembic's job) with "a snapshot of
  the current design" (this directory's job).
- Every table gets a `created_at` / `updated_at` pair via a shared
  `TimestampMixin`, satisfying the "Date Added / Last Updated" requirement
  consistently across entities instead of re-declaring it per model.
- Foreign keys and indexes are added at the point each entity is introduced
  (e.g. `Product.supplier_id`, indexes on `sku`, `barcode`) rather than
  retrofitted — this is called out explicitly in each milestone that adds a
  table.

## 4. Authentication & Authorization

Implemented in Milestone 2 (`app/core/security.py`, `app/api/deps.py`,
`app/api/v1/endpoints/auth.py`).

- **JWT** access tokens (`PyJWT`, HS256, 60-minute default expiry), returned
  from `POST /auth/login`. **bcrypt** (the `bcrypt` package directly) for
  password hashing.
  - Deliberately **not** `python-jose`/`passlib`: both wrapper libraries have
    gone years without a release and have known compatibility issues with
    modern `cryptography`/`bcrypt` releases. `PyJWT` and `bcrypt` are each
    maintained and do exactly one job.
  - The token payload is minimal (`sub` = user id, `exp`); `GET /auth/me`
    resolves the current user from the DB on every request rather than
    trusting a cached role in the token, so a role change or deactivation
    takes effect immediately instead of waiting for the token to expire.
- **Role-Based Access Control**: a `role` enum (`admin`, `manager`,
  `employee`) on the `User` model, persisted as its lowercase string value
  (`values_callable` on the SQLAlchemy `Enum`, not the Python member name) so
  the database, the JSON API contract, and anything querying the DB directly
  all agree on the same strings. `Depends(require_roles(UserRole.ADMIN))`
  gates routes declaratively - authorization is visible in the route
  signature, not buried in the handler body.
- **Self-registration always creates an `EMPLOYEE`** - `AuthService.register`
  ignores any role a client might try to send. `MANAGER`/`ADMIN` accounts can
  only be created by an admin (once user-management endpoints exist) or, to
  bootstrap the very first admin in a fresh environment, via
  `scripts/create_superuser.py`.
- **Token storage is `localStorage`, read by an Axios request interceptor**
  (`frontend/src/api/tokenStorage.ts`) - the standard, simplest approach for
  an SPA talking to a separate API origin. This is a known trade-off (a
  successful XSS could exfiltrate the token; an httpOnly-cookie + CSRF-token
  scheme would close that gap at the cost of meaningfully more moving parts)
  accepted for now and revisited if the project's threat model calls for it.
- Password-reset is a **placeholder**: `POST /auth/password-reset-request`
  validates the input shape and always returns the same generic response, so
  it can't be used to enumerate registered emails - it doesn't send an email
  yet, since there's no notifications/email infrastructure until a later
  milestone.

### Applying RBAC to business resources (Milestone 3+)

Every CRUD module (starting with Suppliers/Categories) follows the same
read/write split: **any authenticated user can read** (`Depends(get_current_user)`),
**only `manager`/`admin` can write** (`Depends(require_roles(UserRole.ADMIN,
UserRole.MANAGER))`) - employees can look up data (to do their jobs -
checking stock, finding a supplier's contact info) but not restructure it.
The frontend mirrors this by hiding write controls (the "Add" button, edit/delete
icons) for a logged-in employee, using the same role check the backend
enforces - this is a UX courtesy (avoid showing buttons that would just 403),
never the actual security boundary, which is always the backend check.

Update endpoints (`PUT`) are a **full replacement**, not a partial `PATCH`:
the request body has the same required fields as create. This matches the
plain `GET`/`POST`/`PUT`/`DELETE` API shape in the project spec and sidesteps
the "does an omitted field mean *don't change it* or *clear it*" ambiguity
partial updates introduce - simpler for both the API and the frontend form,
which always submits every field anyway.

### Cross-entity foreign key validation (Milestone 4+)

`Product` is the first model with foreign keys to other business entities
(`category_id`, `supplier_id`). A database-level FK constraint stops garbage
from ever being persisted, but it fails as a raw `IntegrityError` mid-commit
with a Postgres-flavored message - not something to hand back to an API
client. `ProductService` instead depends on `AbstractCategoryRepository`/
`AbstractSupplierRepository` and checks referenced ids exist *before*
calling `create`/`update`, raising a typed `InvalidCategoryError`/
`InvalidSupplierError` the router maps to a clean `422`. The FK constraint
remains as the actual backstop; the service-layer check exists purely to
turn "invalid input" into a good error message instead of a database
exception leaking through.

### Multi-warehouse inventory model (Milestone 5+)

`Product.current_quantity`/`warehouse_location` (Milestone 4) modeled stock as
a single number attached to the product itself, which cannot represent the
same product sitting in more than one location. Milestone 5 replaces that with
a proper one-to-many relationship: `Warehouse` (a location), `InventoryLevel`
(a `product_id`/`warehouse_id` pair with a `quantity`, unique per pair), and
`InventoryTransfer` (an append-only audit log of stock moved between two
warehouses, recording who performed it and when).

- **Migration, not just a schema change**: `4038b07d5100_add_warehouses_and_
  inventory_tracking.py` creates the new tables, then — before dropping the
  old `products` columns — inserts a "Main Warehouse" and copies every
  existing `products.current_quantity` into an `inventory_levels` row against
  it via raw SQL (`op.execute`/`sa.text()`). Existing data is never silently
  discarded; it's migrated into the new shape as part of the same migration
  that removes the old columns.
- **`Product.total_quantity` is a virtual attribute, not a mapped column** —
  declared only inside an `if TYPE_CHECKING:` block on the model so mypy and
  Pydantic's `from_attributes` validation both see it as a real attribute,
  while `ProductService` attaches the actual value at runtime after a
  `SUM(quantity) GROUP BY product_id` aggregate query
  (`InventoryRepository.get_totals_for_products`). This keeps "how much total
  stock does this product have" a read-time aggregation instead of a
  duplicated, driftable column.
- **Transfers are the only way to move stock between warehouses** —
  `InventoryService.transfer()` validates both warehouses and the product
  exist, checks the source warehouse actually has enough (`InsufficientStock
  Error`, mapped to `409 Conflict`), decrements the source and increments the
  destination, and only then writes an `InventoryTransfer` row. Setting a
  level directly (`PUT /products/{id}/inventory/{warehouse_id}`) is a
  separate, unaudited operation for initial stocking/corrections; moving
  stock between two warehouses always goes through the audited transfer path
  so `transferred_by_id` and the from/to pair are recorded.

### Purchase order status lifecycle (Milestone 6+)

`PurchaseOrder` is the first entity in this system whose primary behavior is
a state machine rather than plain CRUD. `PurchaseOrderStatus` moves strictly
ORDERED -> SHIPPED -> RECEIVED; CANCELLED is reachable from ORDERED or
SHIPPED but never from RECEIVED. That lifecycle is enforced entirely in
`PurchaseOrderService` (`ship`/`receive`/`cancel`, each checking the current
status before calling `PurchaseOrderRepository.update_status`) rather than as
a database constraint - an invalid transition needs to become a clean `409`
with a message naming the attempted action and the current status
(`InvalidStatusTransitionError`), not a constraint-violation error.

- **No DELETE endpoint.** A purchase order is a business record other
  systems (accounting, receiving) may reference; CANCELLED is the intentional
  terminal state for one that shouldn't be acted on further, the same
  reasoning that makes `InventoryTransfer` append-only.
- **Receiving is where inventory changes, not creating.** Creating a PO only
  records intent (nothing is in a warehouse yet); `PurchaseOrderService.
  receive()` is the one place that calls `InventoryRepository.set_level()`,
  adding each line's `quantity_ordered` to whatever is already at the order's
  `warehouse_id` - coordinating the purchase order and inventory repositories
  the same way `InventoryService.transfer()` already coordinates two
  inventory levels within one service method. This milestone always receives
  every line in full; `PurchaseOrderItem.quantity_received` is tracked
  per-line (not just a boolean on the header) so a future partial-receiving
  feature has somewhere to record partial progress without a schema change.
- **Line items use a narrow product summary, not the full `ProductRead`.**
  `PurchaseOrderItemRead` nests id/sku/name/unit_type only. `ProductRead`
  requires `total_quantity`, a virtual attribute the product *service*
  attaches after a separate aggregate query - a `Product` loaded via the
  purchase order's own eager-load never has it set, so reusing `ProductRead`
  here would either crash serialization or require a second, wasted
  aggregate query just to satisfy a field the line item doesn't need anyway.

## 5. Frontend Architecture

```
src/
├── api/          # Axios instance + typed API client functions
├── app/           # App shell: providers, router, theme
├── components/     # Reusable, presentation-only components
├── features/       # Feature-oriented modules (products, sales, dashboard, ...)
├── layouts/         # Page chrome (sidebar, app bar, main layout)
├── hooks/            # Reusable hooks
└── theme/             # MUI theme (light + dark)
```

- **Feature-folder structure** rather than type-first (`components/`,
  `reducers/`, ...) — as the app grows to products, suppliers, purchase orders,
  sales, dashboard, and AI recommendations, colocating a feature's API calls,
  components, and pages keeps related code together and makes each feature
  removable/testable in isolation.
- **TanStack Query (React Query)** is added alongside Axios (not explicitly
  listed in the original stack, called out here as an explicit decision): Axios
  is the HTTP client, React Query owns server-state caching, loading/error
  states, and refetching. Hand-rolling this with `useEffect` + `useState` across
  a dozen list/detail pages is exactly the kind of repeated, error-prone
  boilerplate a "production-quality" app should avoid. Client-only state (auth
  session, theme mode) stays in lightweight React Context — introducing Redux
  for two small pieces of global state would be over-engineering.
- **MUI theme** is structured for light/dark from the start (`theme/index.ts`
  exporting both palettes) even though the toggle UI itself is a later
  milestone — retrofitting theme-aware styling after components are already
  written is significantly more expensive than starting with it.

## 6. Testing Strategy

- **Backend**: pytest, using FastAPI's `TestClient`/`httpx`. Tests run against a
  real PostgreSQL instance (a dedicated `inventory_test` database), not SQLite —
  Postgres-specific behavior (enums, constraints, `ON DELETE` rules) must be
  exercised faithfully. Locally this is the `db` service from Docker Compose; in
  CI it is a Postgres service container. The test database's schema is
  dropped/recreated once per test run (always matching current models
  exactly), and each individual test runs inside its own transaction that's
  rolled back afterward (`backend/tests/conftest.py`), so tests never see each
  other's data without needing per-test schema resets. Repository/service
  separation means business logic can additionally be unit-tested with fake
  repositories where a real DB isn't needed (e.g. `tests/test_deps.py`).
- **Frontend**: React Testing Library + Vitest, colocated with the components
  they test (`Component.test.tsx` next to `Component.tsx`).
- **Top-level `tests/`** is reserved for cross-cutting end-to-end tests that
  exercise the deployed stack as a whole (frontend + backend + DB together) —
  distinct from the unit/integration tests that live next to the code they
  test. It stays empty until a later milestone introduces e2e coverage, so unit
  test iteration speed isn't held back by full-stack test infrastructure.

## 7. Deployment Topology

- Each service (`backend`, `frontend`) owns its own `Dockerfile` (kept next to
  its source, since it describes how to build *that* code). `docker/` holds the
  orchestration: `docker-compose.yml` and any shared compose-level config
  (reverse proxy config, DB init scripts), because compose describes how
  services fit together, not how any one of them is built.
- Configuration is via environment variables (`.env`, never committed;
  `.env.example` documents the required keys) — satisfies 12-factor config and
  keeps secrets out of the repository.

### File storage (Milestone 4+)

Product images are written to a local directory (`UPLOAD_DIR`, default
`backend/uploads/`) and served back via FastAPI's `StaticFiles` at `/static`
(`app/core/storage.py`). This is the simplest thing that works at
dev/demo scale, and every caller goes through `save_product_image()`'s
narrow signature rather than touching the filesystem directly - so swapping
in S3 (or any object store) later, if this ever needs to run across
multiple app instances or scale past a single disk, means changing one
module, not every call site. Uploaded content is validated by declared
content-type (JPEG/PNG/WebP only) and capped at 5MB before it's ever
written to disk.

## 8. Roadmap

See [`ROADMAP.md`](./ROADMAP.md) for the milestone breakdown this architecture
is built up in.
