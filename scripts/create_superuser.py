#!/usr/bin/env python3
"""Create the first admin account.

Public registration (`POST /api/v1/auth/register`) can only ever create
EMPLOYEE accounts - see app/services/auth_service.py for why. This script is
the one legitimate way to create an ADMIN account, and only needs to be run
once per environment to bootstrap access to admin-only features.

Usage (with the backend's virtualenv active, from anywhere):
    python scripts/create_superuser.py --email admin@example.com --full-name "Admin User"

You will be prompted for the password interactively (not passed as an
argument, so it never ends up in shell history).
"""

import argparse
import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402


def create_superuser(email: str, password: str, full_name: str) -> None:
    with SessionLocal() as db:
        repository = UserRepository(db)
        if repository.get_by_email(email) is not None:
            print(f"A user with email {email!r} already exists.", file=sys.stderr)
            sys.exit(1)

        repository.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        print(f"Created admin user {email!r}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    create_superuser(args.email, password, args.full_name)


if __name__ == "__main__":
    main()
