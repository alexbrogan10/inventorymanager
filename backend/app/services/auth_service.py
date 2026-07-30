"""Registration, authentication, and token issuance - the business rules for
auth, independent of HTTP concerns (those live in `app/api/v1/endpoints/auth.py`)
and of persistence details (those live behind `AbstractUserRepository`).
"""

from datetime import timedelta

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import AbstractUserRepository
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    """Raised when registering an email that already has an account."""


class InvalidCredentialsError(Exception):
    """Raised for any login failure - kept generic so the API never reveals
    whether the failure was an unknown email or a wrong password."""


class AuthService:
    def __init__(self, repository: AbstractUserRepository) -> None:
        self._repository = repository

    def register(self, user_in: UserCreate) -> User:
        if self._repository.get_by_email(user_in.email) is not None:
            raise EmailAlreadyRegisteredError(user_in.email)
        return self._repository.create(
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name,
            # Self-registration can never grant anything above the base role -
            # see app/models/user.py.
            role=UserRole.EMPLOYEE,
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self._repository.get_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        return user

    def create_token_for(self, user: User) -> str:
        settings = get_settings()
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        return create_access_token(subject=str(user.id), expires_delta=expires_delta)
