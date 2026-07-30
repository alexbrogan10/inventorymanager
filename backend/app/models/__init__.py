"""SQLAlchemy ORM models.

Every model module should be imported here so that `Base.metadata` is fully
populated for Alembic's autogenerate support. Empty for now - Milestone 2
introduces the first model (`User`).
"""

from app.models.base import Base

__all__ = ["Base"]
