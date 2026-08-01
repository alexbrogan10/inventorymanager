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
                │ (system of │ │ (dashboard│ │ (scikit-learn│
                │  record)   │ │  cache)   │ │  forecasting)│
                │            │ │           │ │              │
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

### Sales: a single-step deduction, not a lifecycle (Milestone 7+)

`Sale` deliberately has no status field. `PurchaseOrder` needs one because a
real-world order genuinely passes through separate states over time
(ordered, then shipped, then received, possibly cancelled first); a sale is
different - it's recorded at the moment it happens, so creating one and
deducting inventory for it are the same event, not two steps separated in
time. Giving `Sale` a status field and a lifecycle service just to mirror
`PurchaseOrder` would be copying that milestone's shape onto a problem that
doesn't have it - there's no PUT or DELETE, no ship/receive/cancel actions,
just `create`, `list`, and `get`.

- **Two-pass validate-then-deduct, not interleaved.** `SaleService.create()`
  first aggregates the requested quantity per `product_id` across every line
  (a sale can list the same product twice), then checks every product has
  enough stock *before* deducting any of them, and only then deducts.
  `InventoryRepository.set_level()` commits immediately on each call with no
  surrounding transaction, so validating and deducting in a single
  interleaved pass could commit a partial deduction before hitting a later
  line's insufficient-stock failure - this order guarantees either the whole
  sale is fulfilled or nothing is deducted. Aggregating first also matters
  by itself: checking two 15-unit lines of the same product independently
  against 20 in stock would pass both checks even though 30 units are
  actually needed.
- **Customer info lives directly on `Sale`, not a separate `Customer`
  entity.** This system has no customer accounts or repeat-customer lookup
  to justify a normalized table; "customer tracking" here means capturing
  who a sale was for, which a few columns on the sale itself already do
  without unused structure.
- **`SaleItem.unit_price` snapshots the price at sale time**, the same
  reasoning as `PurchaseOrderItem.unit_cost`: revenue reporting needs what
  the customer actually paid, which must not drift if the catalog's
  `Product.selling_price` changes later. The frontend's create form
  auto-fills this from the product's current selling price when it's picked,
  but the field stays editable and the value sent is whatever's in the form,
  not a live lookup.

### Dashboard aggregation (Milestone 8+)

The dashboard has no model of its own - every number it shows is computed
from `Product`, `InventoryLevel`, `PurchaseOrder`, and `Sale`/`SaleItem` at
request time. Rather than spreading these across several small endpoints,
there's a single `GET /dashboard/summary` returning one `DashboardSummary`:
one round trip, one loading state on the frontend, and every figure on the
page is guaranteed to reflect the same instant.

- **`DashboardRepository` issues aggregate SQL directly** (`SUM`, `COUNT`,
  `GROUP BY`) rather than composing other repositories' CRUD methods -
  fetching every product and every inventory level into Python to sum them
  would work but pushes work onto the app that Postgres does better.
  `DashboardService` still depends on `AbstractDashboardRepository` (a
  Protocol) like every other service, so it stays unit-testable with a fake
  repository even though there's only one concrete implementation.
- **Low-stock and out-of-stock are mutually exclusive by definition**
  (`0 < total < minimum_quantity` vs. `total == 0`), computed from the same
  grouped query as `InventoryRepository.get_totals_for_products` conceptually
  performs, but scoped to counts rather than per-product totals - so the two
  counters can be summed or shown side by side without double-counting.
- **Recent activity is a merge, not a join.** Sales and purchase orders share
  no table to `UNION` against meaningfully (different columns, different
  domains), so the repository fetches the most recent N of each and the
  service merges and re-sorts by timestamp in Python. This is the one place
  in the codebase that assembles a response schema in the service layer
  instead of returning an ORM instance for the router to serialize - there's
  no `DashboardSummary` table row to return instead.

### Charting (Milestone 8+)

`@mui/x-charts` is added as an explicit dependency (not in the original
stack) for the same reason TanStack Query was in Milestone 3: it's the
narrowest tool that solves the actual problem, and it shares MUI's theme
rather than bringing a second design system's visual language into one
dashboard. The top-sellers chart follows a deliberate, non-default set of
choices rather than "add a chart library and wire up the obvious defaults":

- **Headline numbers are stat tiles, not charts.** Inventory value, product
  counts, and pending-order counts are each a single current number - a KPI
  row of stat tiles reads them faster than five one-bar bar charts would.
- **Stock-health tiles reuse MUI's existing `warning`/`error` palette roles**
  (the same colors `ProductsPage`'s "Low stock" chip already uses) rather
  than introducing new hex values for a "status" channel - one semantic
  meaning, one set of colors, used everywhere it applies.
- **Top sellers is a single-hue bar chart, not a rainbow one.** It's one
  series (quantity sold) across nominal categories (product SKUs); giving
  each bar a different hue would spend the identity channel re-encoding
  information the bar's height already shows, and a single series needs no
  legend box - the card's title already says what's plotted.
- **No pie/donut chart.** Comparing the three stock states as angles is
  harder to read at a glance than the same three numbers as stat tiles,
  which the dashboard already shows individually - a chart was only added
  where a chart was genuinely the better form (ranking products by a
  magnitude), not for every aggregate value.

### Search, filtering, and pagination (Milestone 9+)

`GET /products` gained cross-entity search, five filters, and pagination
rather than staying a flat unfiltered list. This is a breaking change to an
endpoint every other create-flow dropdown (purchase order line items, sale
line items) already depended on - accepted deliberately rather than adding a
second, parallel "search" endpoint, because maintaining two ways to list
products would be the worse ongoing cost. Every caller was updated in the
same milestone: dropdown consumers now request a single generously-sized
page (`page_size=100`) and read `.items`, since this catalog is small enough
that "all of them" and "one large page" are the same thing in practice.

- **The response is always an envelope** (`{items, total, page, page_size}`),
  never a bare array - even a request with no filters at all returns page 1
  of the paginated result. A response shape that changed depending on which
  query parameters were present would need two response models and would
  make the frontend's data-fetching code branch on request params instead of
  always reading `.items`.
- **`stock_status` reuses the exact partition the dashboard already
  established** (Milestone 8's `out_of_stock` = 0, `low_stock` = 0 <
  total < minimum, `in_stock` = total >= minimum) - one definition of what
  "low stock" means, computed the same way everywhere it's asked about,
  rather than each feature inventing its own threshold.
- **Filtering searches and eager-loading share one join, via
  `contains_eager`.** Cross-entity search needs `Category`/`Supplier` joined
  in explicitly (to filter on `Category.name`/`Supplier.company_name`), and
  the response needs them eager-loaded for `CategoryRead`/`SupplierRead` -
  using `joinedload` here as well (as every other product query does) would
  add a *second*, redundant join to the same tables. `contains_eager` tells
  SQLAlchemy the already-written join already has what the relationship
  needs, populating it from there instead.
- **The total-quantity aggregate is computed once, in a subquery joined into
  the same search, not fetched separately per product.** `stock_status` and
  the quantity-range filters all read the same
  `SUM(quantity) GROUP BY product_id` subquery (coalesced to 0 for products
  with no inventory rows at all), so a product can't be "low stock" by one
  filter's math and something else by another's.
- **Count and page queries share their filter conditions**, built once as a
  list and applied to two queries with different `SELECT` targets (`COUNT`
  vs. the full `Product`) - so the reported `total` and the returned `items`
  can never disagree about which products matched.

### Reports & Export (Milestone 10+)

Five reports (`GET /reports/{name}`) are read-only queries over data that
already exists - no new tables. Each accepts `format=json|csv|xlsx`
(default `json`); the router deliberately has no single `response_model=`
per route, since the return type genuinely varies with `format`, and
forcing one shape would mean either lying about the OpenAPI schema or
inventing a wrapper type with no purpose beyond satisfying the decorator.

- **"Power BI export" means CSV/XLSX files, not a live connector.** Power BI
  natively imports both formats, so a file download is a complete, honest
  answer to the requirement; building and maintaining a Power BI connector
  (or an OData/streaming-dataset integration) would be a disproportionate
  amount of infrastructure for a portfolio project's actual reporting needs.
- **CSV uses the stdlib `csv` module; XLSX adds `openpyxl`** as the one new
  dependency this milestone introduces - `app/core/export.py` wraps both
  behind two functions (`to_csv_response`, `to_xlsx_response`) so every
  report endpoint exports the same way. `pandas` is deliberately *not*
  brought in here even though it could do both jobs at once: it's reserved
  for Milestone 12's forecasting pipeline, and pulling it in early to save
  two small functions would front-load an unrelated milestone's dependency.
- **Product movement reuses the dashboard's "merge in Python" pattern**
  (Milestone 8's recent-activity feed) for the same reason: purchase
  receipts, sales, and transfers are three unrelated tables with nothing to
  `UNION` on, so `ReportsRepository` fetches each event type separately and
  `ReportsService` merges them into one `ProductMovementRow` shape and sorts
  by timestamp. The sort direction is the deliberate difference from that
  precedent: recent-activity sorts **descending** because a feed is read
  newest-first, while product movement sorts **ascending** because a ledger
  is read start-to-end, like a bank statement.
- **A purchase order's `updated_at` doubles as its receiving timestamp.**
  There's no separate `received_at` column - `PurchaseOrderService`'s status
  lifecycle (`ORDERED -> SHIPPED -> RECEIVED`, no further edits once
  `RECEIVED`) already guarantees a received order's last write *is* the
  receiving transition, so a second timestamp column would duplicate
  information the table already holds reliably.
- **A transfer produces two ledger rows, not one.** `InventoryTransfer` is a
  single row per movement, but a ledger read from one warehouse's
  perspective needs a signed quantity - so the service emits a
  `transfer_out` row (negative, at `from_warehouse`) and a `transfer_in` row
  (positive, at `to_warehouse`) from each transfer, rather than inventing a
  two-warehouse row shape only this report would need.
- **Supplier performance aggregates in Python, not SQL**, grouping every
  supplier's purchase orders by `supplier_id` after one eager-loaded fetch.
  The metrics involved (average lead time as a timestamp difference,
  on-time rate as a conditional ratio over only `RECEIVED` orders with a set
  `expected_delivery_date`) are awkward to express as portable aggregate SQL
  and this table is small enough that pulling it into the app and reducing
  it there is simpler to read and to test than the equivalent query.

### CSV Data Import (Milestone 11+)

`POST /products/import` (a nested router at `/products/import`, registered
before `products.router` so its literal paths are matched first even though
none of `products.py`'s current routes actually overlap) accepts a CSV file
and creates products from its rows.

- **Each row becomes a `ProductCreate` and goes through
  `ProductService.create` exactly like a single product creation from the
  UI would** - `ProductImportService`'s own job is narrower: parse CSV text,
  resolve `category_name`/`supplier_name` to ids, coerce strings to the
  right types, and turn whatever goes wrong into a row-level error message.
  This means there is exactly one place (`ProductService`) that decides
  what a valid product is, and one set of duplicate-SKU/duplicate-barcode/
  unknown-reference rules - the import path can't drift from the single-
  product path because it's calling the same code, not a reimplementation
  of it.
- **Rows are imported one at a time and committed immediately**, rather
  than validating the whole file before writing anything. A file with 100
  good rows and 1 bad row leaves 100 products created; the bad row is
  reported so the user can fix and re-upload just that one row instead of
  resubmitting a file that was mostly fine. This also means a duplicate SKU
  *within the same file* is caught the same way as a duplicate against an
  existing product: `ProductService.create` looks the SKU up in the
  database, and the first occurrence has already been committed by the
  time the second is checked.
- **`category_name`/`supplier_name`, not ids, are the CSV's foreign-key
  columns.** A spreadsheet a person edits by hand should reference things
  by name, not by an internal database id they'd have to look up first;
  `CategoryRepository.get_by_name`/`SupplierRepository.get_by_company_name`
  (both pre-existing, from Milestone 3) resolve them, and an unresolvable
  name is reported per-row rather than silently skipped.
- **CSV only, not XLSX** - unlike Milestone 10's reports, which export as
  either. The roadmap calls for CSV import specifically, and a single
  input format keeps the parsing path (stdlib `csv`, no new dependency)
  simple; nothing here forecloses adding XLSX import later if it's ever
  asked for.
- **A row's errors are collected and reported together, not stopped at the
  first failure.** A row can be missing a required value *and* have an
  invalid price at the same time; reporting only the first would mean a
  user re-uploads the same row repeatedly, discovering one new problem per
  attempt. Every row failure becomes one `ProductImportRowError` with a
  `messages` list, so a row's full set of problems is visible in a single
  pass.

### AI Forecasting Pipeline (Milestone 12+)

A Random Forest model (`app/ml/model.py`) predicts each product's next
day of demand from its own daily sales history, then a small set of
business rules (`app/services/forecast_service.py`) turns that one number
into a stock-depletion date and a recommended reorder quantity.
`POST /forecasting/train` fits the model from every product's history at
once and persists it to disk (`joblib`); `GET /forecasting/products/{id}/
predict` loads that persisted model and answers for one product. Training
is a separate, explicit action - a predict request never trains on the
caller's behalf, so a slow training run never happens as a surprise side
effect of a read.

- **`pandas` and `scikit-learn` are added now, not earlier**, exactly as
  flagged when `openpyxl` was chosen over `pandas` for Milestone 10's CSV
  export: forecasting is the first feature that actually needs a
  dataframe-shaped feature table and a model to fit, so this is the first
  milestone where the dependency earns its cost.
- **One global model, not one per product.** `product_id` is included as
  a feature alongside calendar and lag features, so the forest learns
  shared patterns (day-of-week seasonality, for instance) across every
  product's history at once rather than fitting a separate small model
  per product - reasonable at this catalog's size, and it means a
  product with only a little history still benefits from patterns
  learned across the rest of the catalog.
- **Feature engineering (`app/ml/features.py`) is pure pandas with no
  database dependency**, separate from `ForecastRepository` (data access)
  and `app/ml/model.py` (the estimator itself). `ForecastRepository`
  returns sparse `(product_id, date, quantity)` rows - one row per day a
  product actually sold something; the feature module is what reindexes
  each product onto a *continuous* daily calendar (zero-filled on no-sale
  days) and computes `lag_1`/`rolling_mean_7`, both shifted by one day so
  a row's features only ever describe days strictly before it. Without
  the zero-fill, gaps between sale days would silently corrupt the
  rolling window; without the shift, a day's target would leak into its
  own features.
- **Confidence comes from the forest's own tree-to-tree disagreement, not
  a second model.** A Random Forest already is an ensemble of trees that
  can each cast a vote; `TrainedModel.predict_with_confidence` predicts
  with every individual tree and reports low confidence when they
  disagree widely relative to their mean, high confidence when they
  agree. This is a property ensembles get for free - a single-estimator
  model (linear regression, for instance) has no equivalent signal to
  offer without deliberately building one.
- **Accuracy is `None` below a minimum row count, not a misleading
  number.** An R² computed from a train/test split of only a handful of
  rows would be noise; `_MIN_ROWS_FOR_EVALUATION = 20` gates whether that
  split (and the resulting accuracy figure) happens at all. The deployed
  model is always refit on every available row regardless - the
  train/test split exists purely to measure accuracy, never to withhold
  data from the model that actually predicts.
- **A product with under a week of continuous history gets a fallback,
  not a model guess.** `build_next_day_feature_row` returns `None` when
  there's too little history for `lag_1`/`rolling_mean_7` to mean
  anything, and the service falls back to the same "top up to
  `minimum_quantity`" policy the rest of the app already uses for
  low-stock - `has_sufficient_history: false` in the response says so
  explicitly rather than presenting a number the model has no real basis
  for.
- **Reorder quantity reuses `minimum_quantity` as its safety-stock
  figure**: predicted demand during the supplier's `lead_time_days`, plus
  `minimum_quantity` as a buffer for after that lead time passes, minus
  stock already on hand. One definition of "how much buffer is enough",
  used everywhere it's asked about, rather than this feature inventing a
  second threshold alongside the one `stock_status` already established
  in Milestone 9.

### Smart Recommendations (Milestone 13+)

`GET /recommendations` is one catalog-wide scan producing four independent
lists - reorder suggestions, overstock warnings, slow-moving products, and
seasonal trends. "Independent" is the operative design decision here:

- **Only reorder suggestions depend on the trained model; the other three
  don't need it at all.** Overstock, slow-moving, and seasonal trends are
  plain aggregations over sales history and `Product.maximum_quantity` -
  no Random Forest involved. `RecommendationsReport.model_trained` tells
  the frontend whether reorder suggestions have anything to show, but a
  never-trained (or stale) model degrades one section of this report
  instead of failing the whole endpoint - a direct consequence of
  Milestone 12's "training is explicit, not implicit" stance: recommending
  reorders is one of several jobs this endpoint does, not a hard
  precondition for the others.
- **Reorder suggestions call `ForecastService.predict()` per product**
  rather than reimplementing its depletion-date/reorder-quantity math a
  second time - the same trade-off Milestone 11's CSV import made by
  routing every row through `ProductService.create()`. One definition of
  "how much to reorder" stays in `ForecastService`; this feature only adds
  the catalog-wide scan and the urgency ordering on top. Each `predict()`
  call reloads the persisted model from disk - N model loads for N
  products rather than one - accepted deliberately at this catalog's
  scale rather than adding a request-scoped model cache prematurely.
- **Overstock reuses `maximum_quantity`, the same way Milestone 9's
  `stock_status` reuses `minimum_quantity` for low-stock.** A product
  already has an explicit, user-set ceiling; "overstock" is honestly just
  "over that ceiling" when one is set. A second, independent signal -
  `days_of_supply` (current stock ÷ the last 60 days' average daily rate)
  - flags products with no `maximum_quantity` at all whose stock would
  still take an unreasonably long time (180+ days) to sell through at
  their recent pace. A product can be flagged for either reason, both, or
  neither; `reasons: list[str]` says which.
- **Slow-moving means "zero sales in the last 60 days while holding
  stock"**, not "low sales" - a product with any recent sales at all,
  however slow, isn't included, keeping this list meaningfully short
  (products that need a decision, not everything below-average). A
  product with zero stock is excluded too: it isn't slow-moving, it's out
  of stock, a distinct and already-handled state. Never-sold products
  (`days_since_last_sale: null`) sort ahead of merely-stale ones, since
  "this has never once sold" is a stronger signal than "this hasn't sold
  in N days."
- **Seasonal trend detection is a plain weekend-vs-weekday average
  ratio**, not a second model - explainable in one sentence and
  verifiable by hand, which matters more here than a fractionally more
  sophisticated statistic would. Below 14 distinct sale-days, or a ratio
  too close to 1 to call a real pattern, a product is simply omitted
  rather than reported with a "no pattern" row - the list only ever
  contains products with something to say.

### Notifications (Milestone 14)

Notifications are system-wide operational alerts - low stock, overstock,
order arrivals, and demand anomalies - not a per-user inbox. This is a
single-tenant system, so "Product X just went below its minimum" is
relevant to whoever's working it, not just whoever happened to trigger the
sale that caused it. There's no message queue or background worker
anywhere in this stack; instead, `NotificationService` is called inline,
synchronously, from `SaleService` and `PurchaseOrderService` at the exact
point the underlying event happens, reusing the same DB session and
transaction that's already open for the sale or receiving action. This
mirrors the service-depends-on-service precedent Milestone 13 set with
`RecommendationService` depending on `ForecastService` - "did something
happen worth telling the user about" is its own concern, layered on top of
"record the sale," not folded into it.

- **Threshold notifications (low stock, overstock) fire only on the
  crossing, not on every check while the condition holds.** `SaleService`
  already computes the before/after quantity for every deducted product,
  and `PurchaseOrderService.receive()` already computes the before/after
  for every received line - `NotificationService.check_for_low_stock`/
  `check_for_overstock` just compare those two numbers against
  `Product.minimum_quantity`/`maximum_quantity` (the same thresholds
  Milestone 9's `stock_status` and Milestone 13's overstock warnings
  already use - one definition, reused a third time) and only create a row
  when the crossing actually happens on this update. Without that check, a
  product sitting below its minimum would generate a new notification on
  every subsequent sale attempt against it.
- **A crossing is deduplicated against existing unread notifications of
  the same type and product**, not against a time window - `has_unread_of_type`
  means the same ongoing breach doesn't spam a second notification until
  the first one is acknowledged (marked read), at which point a recurrence
  is newsworthy again. Order-arrived notifications skip this check
  entirely: receiving a PO is a one-off, already-idempotent action (a
  purchase order can only be received once), so there's nothing to
  deduplicate against.
- **Anomaly detection reuses `ForecastRepository.get_daily_sales_for_product`**
  - the same daily-sales-history query Milestone 12's forecasting and
  Milestone 13's slow-moving/seasonal-trend detection already rely on -
  rather than adding a second "sales by day" data-access path. A day's
  total sells are compared against the average of every other day with at
  least one sale (at least 7 such days required); a day selling 3x that
  average or more is flagged. This is a one-off "look at today" signal, so
  it's deduplicated per product per *day* regardless of read state
  (`has_notification_today`), not per unread notification like the
  threshold types - "unusual demand" stops being relevant once the day
  ends, so acknowledging it early shouldn't let it re-fire before midnight.
- **No websocket or push infrastructure exists in this system**, so the
  bell icon's unread badge and toast pop-ups are both driven by polling
  two lightweight endpoints (`GET /notifications/unread-count` and a
  small page of unread notifications) on a 15-second interval via
  TanStack Query's `refetchInterval`, the same tool every other list page
  already uses for its data fetching - no new client-side dependency
  added for what's fundamentally still "fetch some JSON periodically."
  `NotificationsProvider` (mirroring `AuthProvider`'s
  context/hook/provider split) tracks which notification IDs have already
  been shown as a toast, so a fresh login doesn't toast every notification
  that was already unread before the session started, and a toast is
  queued and shown once per notification, not once per poll.

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

### Frontend UX Polish (Milestone 15)

- **Theme mode is a small dedicated context (`theme/ThemeModeProvider.tsx`),
  not folded into `AuthContext` or a prop threaded through every page** -
  the same context/hook split every other piece of cross-cutting client
  state in this app uses (`AuthContext`, `NotificationsContext`). It starts
  by following the OS-level `prefers-color-scheme` (Milestone 1's original
  default) and only overrides it once the user actually clicks the toggle
  in the `MainLayout` app bar, at which point the choice is written to
  `localStorage` and wins over the OS preference on every future visit. A
  first-time visitor still sees their system's light/dark setting rather
  than a hardcoded one.
- **Sales and Purchase Orders moved onto the same `{items, total, page,
  page_size}` envelope Products and Notifications already use**, rather
  than staying bare, unpaginated lists. Both resources grow without bound
  over the life of the business (unlike Categories/Suppliers/Warehouses,
  small reference-data catalogs that don't need this), so leaving them
  unpaginated was a genuine scaling gap, not just a visual inconsistency -
  the fix touches repository (`list_paginated`), schema (`PaginatedSales`/
  `PaginatedPurchaseOrders`), service, and endpoint layers identically to
  how Milestone 9 paginated Products.
- **One shared `PageLoading` component replaces every page's bare
  `CircularProgress`** - list pages showed an unstyled spinner inline above
  the table, while detail pages returned a bare spinner as the entire page
  content with no centering. Both now render the same centered spinner
  with consistent vertical padding, so a page's loading state looks the
  same regardless of which pattern (inline conditional vs. early return)
  the page happens to use internally.
- **The sidebar drawer is two `Drawer`s, not one made responsive via
  props** - a permanent one shown at `sm` and above, and a temporary
  (overlay) one shown below `sm` and toggled by a hamburger button in the
  app bar. MUI's permanent drawer variant always occupies layout space,
  which is fine on desktop but would eat most of a phone-width viewport;
  swapping to a temporary/overlay drawer below a breakpoint is the
  standard MUI pattern for this, rather than trying to force one `Drawer`
  instance to behave both ways.

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

### Coverage hardening (Milestone 16)

Backend coverage was already at 99% (well past the 80% bar) going into this
milestone from tests written alongside each feature; the one real gap was
`ProductImportService` (86%) - `DuplicateBarcodeError`, a missing-price value,
an invalid `maximum_quantity`, and a `maximum_quantity` below `minimum_quantity`
(a pydantic model-validator failure) all had no test driving them, closed with
four new cases. Two branches (`InvalidCategoryError`/`InvalidSupplierError` from
`ProductService.create`) stay uncovered deliberately: `ProductImportService`
already resolves category/supplier by name and asserts they exist *before*
constructing the row, so by the time `create()` runs those errors cannot
actually fire in this single-threaded, one-row-at-a-time import loop - the
`except` clauses are defensive, not reachable, and contriving a fake service
just to hit them would test the test, not the system.

Frontend coverage needed the real work: every `features/*/api.ts` showed 0%,
because every page test mocks its feature's `api.ts` module entirely (correctly
- pages shouldn't depend on real HTTP). That's a different concern from "does
`api.ts` build the right request", which nothing was verifying. Each feature
gained an `api.test.ts` that mocks the shared `apiClient` instead and asserts
the exact method/URL/params/body `api.ts` sends and the value it returns,
including the two blob-download functions (`downloadReport`,
`downloadImportTemplate`) via `vi.stubGlobal('URL', ...)` and a
`HTMLAnchorElement.prototype.click` spy - the standard way to unit-test a
browser download trigger without a real navigation.

The `useAuth`/`useNotifications` hooks were both bare `useContext` + throw
guards, and both showed 0% because every component test mocks the hook itself
rather than rendering inside a real `AuthProvider`/`NotificationsProvider` -
again correct for a page test, but it left the guard clause itself unverified.
`@testing-library/react`'s `renderHook` (not a bare function call - React's
hook dispatcher needs an actual render pass to be active, or the "no provider"
error is masked by a React-internal "invalid hook call" instead) exercises the
one remaining branch directly.

`CategoriesPage`/`SuppliersPage`/`WarehousesPage` had create and (for two of
three) delete covered, but not edit, cancel, delete-declined, or the
409-conflict error path every `*FormDialog` handles identically - all four
were added to all three pages the same way, since the pages share one
generator template (see Milestone 3). `SalesPage`/`PurchaseOrdersPage`/
`NotificationsPage` had their `TablePagination` wiring (added in Milestone 15)
completely untested - "next page" and "change rows per page" tests were added
to all three, following the same request-shape assertion style as everything
else.

One latent bug surfaced repeatedly while adding these: page-test files that
never call `vi.clearAllMocks()` between tests let `mock.calls` accumulate
across the whole file, so a later test's `not.toHaveBeenCalled()` or
`mock.calls[0]` assertion can be silently corrupted by an earlier test's call
to the same mocked function. Every test file touched in this milestone now
has a `beforeEach(() => vi.clearAllMocks())` - cheap insurance against a class
of bug that only shows up as a flaky-looking failure in an unrelated test.

### CI/CD Pipeline (Milestone 18)

`.github/workflows/ci.yml` runs on every push/PR to `main` as three jobs:

- **`backend`**: `ruff check` (lint) → `ruff format --check` (format) → `mypy`
  (types) → `pytest` (test), against real `postgres` and `redis` service
  containers - the same real-Postgres testing philosophy from Section 6
  extends to Redis once Milestone 17 gave the test suite cache-backed
  fixtures to run. This job was silently broken from the Milestone 17 merge
  onward: `test_dashboard.py`'s `TestCaching` cases and the `redis_client`
  fixture's `flushdb()` calls need a reachable Redis, and `ci.yml` only ever
  provisioned `postgres`, so every dashboard test failed with
  `redis.exceptions.ConnectionError`. Adding a `redis:7-alpine` service
  container (mirroring the existing `postgres` block) fixed it - the kind of
  gap that's invisible until something forces you to actually look at CI
  history rather than assume the last green run is still representative.
- **`frontend`**: `oxlint` (lint) → `prettier --check` (format) → `vitest`
  (test) → `vite build` (build), unchanged from Milestone 1.
- **`docker-build`** (new): actually builds the Milestone 17 Dockerfiles -
  the backend's `runtime` target and the frontend's `prod` target - via a
  matrix job using `docker/build-push-action` with `push: false` (nothing is
  published; a successful build is the check) and GitHub Actions' layer
  cache (`cache-from`/`cache-to: type=gha`) so repeat runs only rebuild
  changed layers. This is the first time either Dockerfile is verified by an
  actual `docker build` rather than `docker compose config`'s YAML-only
  validation - hosted GitHub runners have a Docker daemon where the
  Dockerfiles were authored, so a syntax or dependency mistake that
  `docker compose config` can't see (a missing `COPY` source, a broken
  multi-stage reference) now fails CI instead of surfacing only at deploy
  time. `needs: [backend, frontend]` gates it behind the fast lint/test jobs,
  so a broken PR fails in about a minute rather than waiting on a multi-stage
  image build first.

## 7. Deployment Topology

- Each service (`backend`, `frontend`) owns its own `Dockerfile` (kept next to
  its source, since it describes how to build *that* code). `docker/` holds the
  orchestration: `docker-compose.yml` (dev) and `docker-compose.prod.yml`
  (production-shaped), plus `.env.example` for the secrets the latter needs -
  compose describes how services fit together, not how any one of them is
  built.
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

### Full Dockerization (Milestone 17)

- **Multi-stage backend image**: a `builder` stage installs dependencies
  into a venv; the `runtime` stage copies just that venv plus the app code
  onto a fresh `python:3.13-slim`, so pip's cache and any build-only tooling
  never ship in what actually runs. `docker-compose.yml` (dev) still targets
  `runtime` (with `--reload` and a bind mount over it) rather than adding a
  third stage - dev and prod run the same image, just with different
  `command`/`volumes`.
- **Production frontend image**: `nginx-unprivileged` (not stock `nginx`)
  so the container runs as a non-root user without hand-patching file
  permissions, listening on 8080. `frontend/nginx.conf` gzips text assets,
  sets security headers (a locked-down CSP, `X-Frame-Options`,
  `X-Content-Type-Options`), caches Vite's content-hashed `/assets/` forever
  while forcing `index.html` to always revalidate, and reverse-proxies
  `/api/` and `/static/` to the `backend` service. That last point is what
  makes the frontend the **only** public entry point in production - the
  browser calls its own origin for everything, `VITE_API_BASE_URL` is baked
  in at build time as the relative path `/api/v1`, and CORS becomes a
  non-issue (same-origin) rather than something to configure. `api/client.ts`'s
  `apiOrigin` (used for product image URLs) falls back to
  `window.location.origin` when the configured base URL is relative, since
  `new URL()` can't resolve a relative string without a base.
- **`docker-compose.prod.yml`** is a separate file from the dev compose, not
  a dev-plus-overrides layer, because production differs in kind, not just
  configuration: no bind mounts/`--reload`, `db`/`redis` publish no ports to
  the host (only `frontend` is public, everything else is reachable only on
  the compose network), every service has `restart: unless-stopped`, and
  secrets (`POSTGRES_PASSWORD`, `SECRET_KEY`) use compose's `${VAR:?message}`
  syntax so the stack refuses to start with them unset rather than silently
  running with an insecure default - trying to express all of that as
  overrides on the dev file would obscure more than it'd share.
- **Redis is wired to something real, not just provisioned**: it caches
  `GET /dashboard/summary` (the one endpoint that aggregates across
  products, sales, and purchase orders on every load) for
  `DASHBOARD_CACHE_TTL_SECONDS` (default 30s) - short enough that stale
  inventory numbers are never misleading for long, long enough to
  meaningfully cut repeated-visit DB load. `app/core/cache.py`'s `Cache`
  wrapper treats Redis as pure cache-aside: every method catches
  `redis.RedisError` and degrades to a no-op (a miss on read, a silent drop
  on write) rather than raising, with a 1-second connect/socket timeout so
  an unreachable Redis costs at most a second, never a hung request. A cache
  outage should only ever cost performance, never availability - confirmed
  by a test that points `REDIS_URL` at an unroutable address and asserts the
  dashboard still returns 200 with correct data. Tests get their own
  logical DB (`TEST_REDIS_URL`, DB 1, flushed before/after each test) so
  cache state from one test run never leaks into the next, the same
  isolation principle `TEST_DATABASE_URL` already established for Postgres.
- **Environment variable audit**: `backend/.env.example` and
  `frontend/.env.example` document every variable the *application code*
  reads; `docker/.env.example` is a separate, smaller surface - only the
  handful of values that must differ per production deployment
  (`POSTGRES_PASSWORD`, `SECRET_KEY`, `CORS_ORIGINS`, `FRONTEND_PORT`).
  Everything else in `docker-compose.prod.yml` is either a fixed
  service-name URL (`redis://redis:6379/0`) or has a safe compose-level
  default (`POSTGRES_USER`) - there's no reason to make an operator
  re-specify a value that's the same in every deployment.

## 8. Roadmap

See [`ROADMAP.md`](./ROADMAP.md) for the milestone breakdown this architecture
is built up in.
