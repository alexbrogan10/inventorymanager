# Development Roadmap

This project is built one milestone at a time. Each milestone produces a working,
demoable increment of the system — never a partial/broken state — and ends with a
commit before the next one starts. See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for
the reasoning behind the layering and folder structure referenced below.

Status legend: ✅ done · 🚧 in progress · ⬜ not started

| # | Milestone | Summary | Status |
|---|---|---|---|
| 1 | **Project Foundation & Dev Environment** | Repo structure, FastAPI skeleton, Postgres + Alembic wired up, React/Vite/TS/MUI skeleton, Docker Compose for local dev, CI skeleton (lint + test), linting/formatting config. | ✅ |
| 2 | **Authentication & Authorization** | `User` model + roles (Admin/Manager/Employee), register/login, JWT issuing & verification, bcrypt hashing, password-reset placeholder, RBAC dependency guards, frontend login/register pages + auth context + protected routes. | ✅ |
| 3 | **Suppliers & Categories** | First full vertical slice (API + service + repository + frontend CRUD pages) — establishes the template every later module follows. | ✅ |
| 4 | **Products** | Full product model (SKU, barcode, pricing, quantities, warehouse location, image), CRUD API + validation, product list/detail/form UI. | ✅ |
| 5 | **Warehouses & Inventory Transfers** | Multiple warehouse locations, per-warehouse stock levels, transfer-between-warehouses workflow. | ✅ |
| 6 | **Purchase Orders** | Create purchase orders, status lifecycle (Ordered → Shipped → Received → Cancelled), receiving a PO increments inventory. | ✅ |
| 7 | **Sales** | Record sales, automatic inventory deduction, revenue/customer/employee tracking. | ✅ |
| 8 | **Dashboard** | Aggregation endpoints (inventory value, low/out-of-stock counts, pending orders, recent activity, top sellers) + frontend dashboard with charts. | ✅ |
| 9 | **Search & Filtering** | Cross-entity search (product/SKU/barcode/supplier/category) and filters (category/warehouse/supplier/quantity/stock status), with pagination. | ✅ |
| 10 | **Reports & Export** | Inventory valuation, sales history, purchase history, product movement, supplier performance reports; CSV/Excel/Power BI export. | ✅ |
| 11 | **CSV Data Import** | Bulk product import with validation (required columns, missing values, duplicate SKUs, invalid prices/quantities) and a detailed error report UI. | ✅ |
| 12 | **AI Forecasting Pipeline** | Random Forest model for demand forecasting, stock depletion date, and reorder quantity; `/predict` API; confidence score, feature importance, and accuracy surfaced to the frontend. | ✅ |
| 13 | **Smart Recommendations** | Built on Milestone 12: reorder suggestions, overstock warnings, slow-moving inventory, seasonal trend detection. | ✅ |
| 14 | **Notifications** | Threshold breaches, order arrivals, overstock, anomaly detection; notification center + toasts in the UI. | ✅ |
| 15 | **Frontend UX Polish** | Dark/light mode toggle, consistent loading states, responsive layout pass, table/pagination consistency across all modules. | ✅ |
| 16 | **Testing Hardening** | Close gaps to reach 80%+ backend coverage; component + API test coverage on the frontend. | ✅ |
| 17 | **Full Dockerization** | Production-shaped Docker Compose (backend, frontend, Postgres, Redis), multi-stage builds, environment variable audit. | ✅ |
| 18 | **CI/CD** | GitHub Actions: test, lint, format checks on every PR; build check for both services. | ✅ |
| 19 | **Documentation Suite** | Final README, API docs, ER diagram, installation/developer/deployment guides, future roadmap write-up. | ✅ |

## Why this order

- **1–2** establish the skeleton and security foundation everything else sits on.
- **3** is deliberately the *simplest possible* full vertical slice (no
  cross-entity relationships to speak of) so the API → service → repository →
  frontend pattern gets proven out once, cheaply, before Products (4) — which
  depends on Suppliers and Categories existing — builds on it.
- **5–7** (warehouses, purchase orders, sales) are the core transactional
  features, ordered by dependency: sales needs inventory to deduct from,
  purchase orders need suppliers, both need warehouses to attribute stock to.
- **8–11** turn the transactional data into business value: dashboard, search,
  reports, import — all read/aggregate existing data, so they come after the
  data-producing features exist.
- **12–14** are the AI/ML differentiators. They deliberately come after there's
  real transactional history (sales, purchases) to train and demo against —
  building a forecasting model against an empty database would be untestable
  and unconvincing.
- **15–19** are cross-cutting hardening passes (UX consistency, test coverage,
  deployment, CI, docs) that are cheapest to do once the feature set is stable,
  rather than repeatedly redone after every feature milestone.

Each milestone will end with a summary of exactly what to `git commit`, and a
realistic commit message, before moving to the next one.

## Beyond Milestone 19

Milestone 19 completes the originally-planned scope. What follows are gaps
and extensions identified along the way — deliberately deferred because they
either aren't needed at this project's current scale or belong to a
different problem than the one each milestone was solving, not because
they were missed by accident.

| Idea | Why it's not already done |
|---|---|
| **Real password reset** | `POST /auth/password-reset-request` is a placeholder today (see `app/api/v1/endpoints/auth.py`) — it validates the request and returns a generic response, but sends no email and issues no reset token. Needs an email-sending integration, which nothing in this stack currently provides. |
| **"Promote user" endpoint** | Creating an `admin`/`manager` account beyond the first one currently means either running `scripts/create_superuser.py` again or editing the `users` table directly — there's no API for an existing admin to promote another user's role. |
| **Object storage for product images** | `app/core/storage.py` writes to local disk by design (see `ARCHITECTURE.md` section 7) — correct at single-instance scale, but would need swapping for S3-or-compatible storage before running more than one backend replica, since local disk isn't shared across containers. |
| **Populated `sample_data/`, `powerbi/`, `database/seeds/`** | All three directories exist with a README describing their intended purpose but no actual files — every environment today is seeded via `scripts/create_superuser.py` plus manually using the product import feature, not a fixed demo dataset. |
| **Real-time notifications** | The notification bell/toasts (Milestone 14) are populated by polling `GET /notifications` on an interval, not pushed — a websocket or SSE channel would remove the polling latency, at the cost of infrastructure this project hasn't otherwise needed. |
| **End-to-end test suite** | `tests/` at the repo root is reserved for full-stack tests (frontend + backend + DB together) but has stayed empty — unit/integration coverage (Milestone 16) has been sufficient so far, and e2e infra (a real browser, a seeded environment) is a nontrivial addition on its own. |
| **Multi-tenancy** | Every table is implicitly single-tenant (e.g. `notifications` are system-wide, not scoped to an organization). Adding real multi-tenancy would touch nearly every table and query in the system — a decision big enough that it shouldn't be retrofitted incidentally alongside something else. |
| **Rate limiting** | No rate limiting exists on `/auth/login` or any other endpoint today. Fine for a portfolio/demo deployment; a public production deployment would want it in front of auth endpoints at minimum. |
| **SSO / OAuth login** | Auth is email+password only. An organization deployment would likely want SSO (SAML/OIDC) instead of managing passwords directly. |
| **Additional forecasting models** | The forecasting pipeline (Milestone 12) uses a single Random Forest model; the `app/ml/` module's model wrapper was written to make swapping in or A/B-testing another model (e.g. gradient boosting) straightforward, but no second model has been built yet. |
| **Horizontal scaling for `db`/`redis`** | Both run as single instances with no replication (see `DEPLOYMENT.md`'s scaling notes) — appropriate for this project's current scale, revisit if that changes. |
