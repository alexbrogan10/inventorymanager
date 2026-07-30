"""The `User` model and its role enum.

Every account has exactly one role. Public self-registration (see
`AuthService.register`) always creates `EMPLOYEE` accounts - promoting a user
to `MANAGER`/`ADMIN` is an administrative action, not something a user can
grant themselves. The very first admin account is created out-of-band via
`scripts/create_superuser.py`.
"""

import enum

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


def _enum_values(members: type[UserRole]) -> list[str]:
    return [member.value for member in members]


# Without values_callable, SQLAlchemy stores the Python enum *names*
# (ADMIN/MANAGER/EMPLOYEE) rather than the lowercase .value strings - forcing
# it to use .value keeps the DB, the API/JSON contract (via UserRole's str
# value), and anything querying the DB directly all in agreement.
_user_role_column_type = SqlEnum(
    UserRole, name="user_role", native_enum=True, values_callable=_enum_values
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_user_role_column_type, default=UserRole.EMPLOYEE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
