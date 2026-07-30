"""Unit tests for `require_roles` - exercised directly as a plain function
rather than through the API, since it's pure authorization logic with no
I/O. (End-to-end coverage of the auth *flow* itself, including
`get_current_user`, lives in test_auth.py.)
"""

import pytest
from fastapi import HTTPException

from app.api.deps import require_roles
from app.models.user import User, UserRole


def _make_user(role: UserRole) -> User:
    return User(
        id=1,
        email="user@example.com",
        hashed_password="x",
        full_name="Test User",
        role=role,
        is_active=True,
    )


def test_allows_a_user_with_one_of_the_allowed_roles() -> None:
    check = require_roles(UserRole.ADMIN, UserRole.MANAGER)
    admin = _make_user(UserRole.ADMIN)

    assert check(admin) is admin


def test_denies_a_user_without_an_allowed_role() -> None:
    check = require_roles(UserRole.ADMIN)
    employee = _make_user(UserRole.EMPLOYEE)

    with pytest.raises(HTTPException) as exc_info:
        check(employee)

    assert exc_info.value.status_code == 403
