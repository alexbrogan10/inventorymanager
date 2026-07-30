# Scripts

Developer convenience scripts. Run with the backend's virtualenv active
(these import the `app` package from `../backend`).

- **`create_superuser.py`** — creates the first ADMIN account. Public
  self-registration can only create EMPLOYEE accounts (by design - see
  `backend/app/services/auth_service.py`), so this is how you bootstrap
  access to admin-only features in a fresh environment:

  ```bash
  cd backend && source .venv/bin/activate && cd ..
  python scripts/create_superuser.py --email admin@example.com --full-name "Admin User"
  ```

More scripts (database seeding, demo data generation) arrive in later
milestones.
