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
| 17 | **Full Dockerization** | Production-shaped Docker Compose (backend, frontend, Postgres, Redis), multi-stage builds, environment variable audit. | ⬜ |
| 18 | **CI/CD** | GitHub Actions: test, lint, format checks on every PR; build check for both services. | ⬜ |
| 19 | **Documentation Suite** | Final README, API docs, ER diagram, installation/developer/deployment guides, future roadmap write-up. | ⬜ |

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
