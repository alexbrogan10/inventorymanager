# AI Inventory Management System

A full-stack inventory management platform for tracking products, suppliers,
purchase orders, sales, and multi-warehouse stock — with a machine learning
layer that forecasts demand and recommends reorder quantities.

> **Status:** All 19 planned milestones complete — authentication/RBAC, full
> inventory/purchasing/sales workflows, AI demand forecasting and
> recommendations, notifications, a hardened test suite, production
> Dockerization, CI/CD, and this documentation suite. Built
> milestone-by-milestone; see [`docs/ROADMAP.md`](docs/ROADMAP.md) for the
> full history and what's identified as future work beyond the original
> scope.

## Tech Stack

| | |
|---|---|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn |
| **AI / ML** | Pandas, scikit-learn (Random Forest, expandable to XGBoost) |
| **Frontend** | React, TypeScript, Vite, Material UI, React Router, Axios, TanStack Query, MUI X Charts |
| **Database** | PostgreSQL |
| **Auth** | JWT + bcrypt |
| **Cache** | Redis (dashboard summary caching) |
| **Testing** | pytest, React Testing Library / Vitest |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

## Documentation

- [Installation Guide](docs/INSTALLATION.md) — Docker Compose or manual
  setup, environment variables, creating the first admin user
- [API Reference](docs/API.md) — auth model, RBAC, endpoint map (the
  authoritative reference is the live Swagger UI at `/docs`; this is the map
  to it)
- [ER Diagram](database/schema/ER_DIAGRAM.md) and
  [reference SQL schema](database/schema/schema.sql) — the data model
- [Developer Guide](docs/DEVELOPER_GUIDE.md) — repo layout, the vertical-slice
  pattern used for every feature, testing/linting/migrations workflow
- [Deployment Guide](docs/DEPLOYMENT.md) — running the production Docker
  Compose stack on a real server
- [Architecture Overview](docs/ARCHITECTURE.md) — system design and the
  reasoning behind it
- [Development Roadmap](docs/ROADMAP.md) — milestone breakdown and future work

## Project Structure

```
inventorymanager/
├── backend/        # FastAPI application (API, services, repositories, models)
├── frontend/        # React + TypeScript SPA
├── database/         # ER diagram, reference schema, seed data docs
├── docker/            # docker-compose.yml and shared orchestration config
├── docs/               # Architecture, roadmap, API/installation/developer/deployment docs
├── scripts/             # Developer convenience scripts
├── sample_data/           # Sample CSVs for import / demo seeding
├── powerbi/                # Power BI-ready export templates
└── tests/                   # Cross-service end-to-end tests
```

## Getting Started (local development)

Requirements: Docker and Docker Compose.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose -f docker/docker-compose.yml up --build
```

- Backend API: http://localhost:8000 (interactive docs at `/docs`)
- Frontend: http://localhost:5173

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md) for the full walkthrough
— including running each service manually without Docker, the complete
environment variable reference, and creating the first admin account (public
registration can only create read-only accounts by design). For running this
on a real server instead of your own machine, see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## License

[MIT](LICENSE)
