"""Registration, login, current-user, and password-reset-request endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import PasswordResetRequest, Token, UserCreate, UserRead
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, service: AuthService = Depends(get_auth_service)) -> User:
    try:
        return service.register(user_in)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        ) from exc


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    # OAuth2PasswordRequestForm's field is named "username" by spec; this API
    # uses email as the username.
    try:
        user = service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return Token(access_token=service.create_token_for(user))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password-reset-request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest) -> dict[str, str]:
    """Placeholder: no email is actually sent yet (that arrives with a future
    notifications milestone). Always returns the same generic response
    regardless of whether the address is registered, so this endpoint can't be
    used to enumerate accounts.
    """
    return {"message": "If that email is registered, a password reset link will be sent."}
