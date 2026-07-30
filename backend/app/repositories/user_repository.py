"""Data access for `User`.

`AbstractUserRepository` is what `AuthService` actually depends on (Dependency
Inversion, per docs/ARCHITECTURE.md) - it lets services be unit-tested against
an in-memory fake instead of a real database. `UserRepository` is the real,
SQLAlchemy-backed implementation wired up via FastAPI's `Depends()` in
`app/api/v1/endpoints/auth.py`.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class AbstractUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def create(
        self, *, email: str, hashed_password: str, full_name: str, role: UserRole
    ) -> User: ...


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def create(self, *, email: str, hashed_password: str, full_name: str, role: UserRole) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
