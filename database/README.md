# Database

This directory is documentation, not code — the live schema history lives in
[`../backend/alembic/versions/`](../backend/alembic/versions) since migrations
are generated from and coupled to the SQLAlchemy models in `backend/app/models/`.

What belongs here (added as the corresponding entities are built):

- `schema/` — a plain-SQL reference schema and the ER diagram, for anyone who
  wants to understand the data model without running the app.
- `seeds/` — seed data definitions used by `scripts/` to populate a fresh
  database with demo data.

Empty until Milestone 3 introduces the first real tables (Suppliers,
Categories).
