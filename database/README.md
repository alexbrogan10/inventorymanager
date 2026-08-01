# Database

This directory is documentation, not code — the live schema history lives in
[`../backend/alembic/versions/`](../backend/alembic/versions) since migrations
are generated from and coupled to the SQLAlchemy models in `backend/app/models/`.

- [`schema/schema.sql`](schema/schema.sql) — a plain-SQL reference schema
  (all 12 tables, matching the current migrations) for anyone who wants to
  read the data model without running the app or a migration tool.
- [`schema/ER_DIAGRAM.md`](schema/ER_DIAGRAM.md) — a Mermaid
  entity-relationship diagram of the same model, with notes on the
  non-obvious relationships (why `products` has no quantity column, why
  `notifications` links to either a product or a purchase order but never
  both, etc).
- `seeds/` — reserved for seed data definitions, not yet populated; every
  environment today is seeded via `scripts/create_superuser.py` plus the
  product CSV import feature rather than a fixed seed script.
