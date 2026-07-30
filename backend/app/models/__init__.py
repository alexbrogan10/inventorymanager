"""SQLAlchemy ORM models.

Every model module is imported here so that `Base.metadata` is fully
populated for Alembic's autogenerate support.
"""

from app.models.base import Base
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.user import User, UserRole

__all__ = ["Base", "Category", "Supplier", "User", "UserRole"]
