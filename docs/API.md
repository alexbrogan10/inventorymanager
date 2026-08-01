# API Reference

The backend is a FastAPI application, which means the authoritative,
always-up-to-date API reference is generated automatically from the code —
this document is a map to help you navigate it, not a duplicate of it.

## Interactive docs

With the backend running (see [`INSTALLATION.md`](./INSTALLATION.md)):

| | |
|---|---|
| **Swagger UI** | http://localhost:8000/docs — try requests directly in the browser, including the "Authorize" button for JWT auth. |
| **ReDoc** | http://localhost:8000/redoc — a read-only, more skimmable rendering of the same spec. |
| **Raw OpenAPI schema** | http://localhost:8000/openapi.json (also linked from both UIs above) |

Every request/response schema, validation rule, and status code documented
below is generated from the same Pydantic models (`backend/app/schemas/`)
that FastAPI uses to validate real requests — the interactive docs cannot
drift from the implementation the way hand-written API docs can.

## Base URL & versioning

All routes are mounted under `/api/v1` (`app/core/config.py`'s
`api_v1_prefix`). There is no `/v2` yet; if one is ever introduced, `/api/v1`
keeps working unchanged rather than being an alias for "latest."

## Authentication

JWT bearer tokens, issued by `POST /api/v1/auth/login` (OAuth2 password
grant form: `username` + `password`, `username` being the user's email).

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=your-password"
# → {"access_token": "...", "token_type": "bearer"}

curl http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer <access_token>"
```

Every route except `POST /auth/register`, `POST /auth/login`,
`POST /auth/password-reset-request`, and the two `/health/*` checks requires
this header. A missing or invalid token returns `401` with
`WWW-Authenticate: Bearer`.

### Roles (RBAC)

Every user has exactly one role, set at `Depends(get_current_user)` /
`Depends(require_roles(...))` time (`app/api/deps.py`):

| Role | Can do |
|---|---|
| **Employee** | Read everything (catalog, inventory, purchase orders, sales, dashboard, reports, recommendations) and acknowledge notifications. Cannot create or modify anything. |
| **Manager** | Everything an Employee can, plus every mutation: create/update/delete catalog data (products, categories, suppliers, warehouses), create/ship/receive/cancel purchase orders, record sales, import products via CSV, train the forecasting model. |
| **Admin** | Everything a Manager can. No additional API-level permission exists today beyond Manager — the distinction mainly matters for `scripts/create_superuser.py` (the only way to mint the first account) and is reserved for future admin-only operations. |

Public self-registration (`POST /auth/register`) can only ever create
`employee` accounts; the first `admin`/`manager` account must be created via
`scripts/create_superuser.py` or promoted by an existing admin directly in
the database (no "promote user" endpoint exists yet).

Concretely: every `GET` endpoint requires only a valid token (any role).
Every `POST`/`PUT`/`PATCH`/`DELETE` that mutates catalog, inventory,
purchase-order, or sale data requires `admin` or `manager` via
`Depends(require_roles(...))` — an `employee` token gets `403 Forbidden`.
The one exception is `PATCH /notifications/*` (marking a notification read),
which only needs a valid token: acknowledging an alert isn't a business-data
mutation, so it doesn't need the write role.

## Response conventions

- **Success**: the resource (or list of resources) as JSON, `201 Created`
  for creation endpoints, `204 No Content` for deletes.
- **Validation errors** (`422`): FastAPI/Pydantic's standard shape —
  `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.
- **Domain errors** (`404`, `409`, `422` business-rule violations): a
  simpler `{"detail": "human-readable message"}`, raised as `HTTPException`
  in each endpoint module after catching a domain-specific exception from
  the service layer (e.g. `ProductNotFoundError` → 404, `DuplicateSkuError`
  → 409). See `docs/ARCHITECTURE.md` section 2 for why errors are translated
  at the API layer rather than the service layer knowing about HTTP.

## Pagination

`GET /products`, `GET /sales`, `GET /purchase-orders`, and
`GET /notifications` accept `page`/`page_size` query params and return:

```json
{ "items": [ ... ], "total": 137, "page": 1, "page_size": 20 }
```

Every other list endpoint (`categories`, `suppliers`, `warehouses`) returns
a plain JSON array — those entities are expected to stay small (tens, not
thousands, of rows) so pagination would be overhead without benefit.

## Endpoint map

| Resource | Routes | Notes |
|---|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/password-reset-request` | Register always creates an `employee`. |
| **Categories** | `GET/POST /categories`, `GET/PUT/DELETE /categories/{id}` | |
| **Suppliers** | `GET/POST /suppliers`, `GET/PUT/DELETE /suppliers/{id}` | |
| **Products** | `GET/POST /products`, `GET/PUT/DELETE /products/{id}`, `POST /products/{id}/image`, `GET /products/{id}/inventory`, `PUT /products/{id}/inventory/{warehouse_id}`, `POST /products/{id}/transfer` | List supports search/filter/pagination (Milestone 9). Inventory routes read/write per-warehouse `InventoryLevel` rows. |
| **Product Import** | `GET /products/import/template`, `POST /products/import` | Template download is a CSV skeleton; import returns a per-row success/error report. |
| **Warehouses** | `GET/POST /warehouses`, `GET/PUT/DELETE /warehouses/{id}` | |
| **Purchase Orders** | `GET/POST /purchase-orders`, `GET /purchase-orders/{id}`, `POST /purchase-orders/{id}/ship`, `POST /purchase-orders/{id}/receive`, `POST /purchase-orders/{id}/cancel` | Status lifecycle: `ordered → shipped → received`, or `→ cancelled` from `ordered`/`shipped`. Receiving increments `InventoryLevel`. |
| **Sales** | `GET/POST /sales`, `GET /sales/{id}` | Creating a sale immediately deducts inventory; sales are never edited or deleted. |
| **Dashboard** | `GET /dashboard/summary` | Aggregated KPIs; cached in Redis for `DASHBOARD_CACHE_TTL_SECONDS` (default 30s). |
| **Reports** | `GET /reports/{inventory-valuation,sales-history,purchase-history,product-movement,supplier-performance}` | All 5 accept `?format=json\|csv\|xlsx`; csv/xlsx return a file download instead of JSON. |
| **Forecasting** | `POST /forecasting/train`, `GET /forecasting/products/{product_id}/predict` | Train is Manager/Admin only (compute cost); predict is a read for any role. |
| **Recommendations** | `GET /recommendations` | Reorder, overstock, slow-moving, and seasonal-trend suggestions built on the forecasting pipeline. |
| **Notifications** | `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/read-all`, `PATCH /notifications/{id}/read` | System-wide, not per-user — a low-stock alert is relevant to every user. |
| **Health** | `GET /health/live`, `GET /health/ready` | No auth required; `ready` checks the DB connection (used by Docker `HEALTHCHECK`). |

For exact request/response bodies, query parameters, and status codes for
any route above, open it in Swagger UI (`/docs`) — every field there,
including whether it's optional and its validation constraints, reflects
the real Pydantic schema.
