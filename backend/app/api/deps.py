"""Request-scoped auth dependencies shared by every protected route.

Lives in the API layer (not `core/`) because it depends on `repositories/`
and `models/`, and `core/` must stay free of upward dependencies (see
docs/ARCHITECTURE.md).
"""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# tokenUrl only affects the URL Swagger UI's "Authorize" button posts a login
# form to - it does not register or mount a route itself.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise _CREDENTIALS_ERROR from exc

    user = UserRepository(db).get_by_id(int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory for RBAC: `Depends(require_roles(UserRole.ADMIN))`.

    Declaring the allowed roles in the route signature (rather than checking
    inside the handler body) keeps authorization visible at a glance and
    consistent across every endpoint that needs it.
    """

    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _check_role
