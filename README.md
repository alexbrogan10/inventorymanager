# AI Inventory Management System

A full-stack inventory management platform for tracking products, suppliers,
purchase orders, sales, and multi-warehouse stock — with a machine learning
layer that forecasts demand and recommends reorder quantities.

> **Status:** Under active development. Built milestone-by-milestone; see
> [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's done and what's next.

## Tech Stack

| | |
|---|---|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn |
| **AI / ML** | Pandas, scikit-learn (Random Forest, expandable to XGBoost) |
| **Frontend** | React, TypeScript, Vite, Material UI, React Router, Axios, TanStack Query, MUI X Charts |
| **Database** | PostgreSQL |
| **Auth** | JWT + bcrypt |
| **Cache** | Redis (introduced in a later milestone) |
| **Testing** | pytest, React Testing Library / Vitest |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) — system design and the
  reasoning behind it
- [Development Roadmap](docs/ROADMAP.md) — milestone breakdown

## Project Structure

```
inventorymanager/
├── backend/        # FastAPI application (API, services, repositories, models)
├── frontend/        # React + TypeScript SPA
├── database/         # ER diagram, reference schema, seed data docs
├── docker/            # docker-compose.yml and shared orchestration config
├── docs/               # Architecture, roadmap, and (later) API/deployment docs
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

Running the services without Docker, running tests, and the full developer
workflow are documented in [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md).

A full Installation Guide, Developer Guide, and Deployment Guide will be
added to `docs/` in the Documentation milestone, once the corresponding
subsystems exist to document.

## License

[MIT](LICENSE)
