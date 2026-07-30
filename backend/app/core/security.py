"""Password hashing and JWT helpers.

Uses `bcrypt` and `PyJWT` directly rather than `passlib`/`python-jose`: both
of those wrapper libraries have gone years without a release and have known
compatibility issues with modern `bcrypt`/`cryptography` releases, while
`bcrypt` and `PyJWT` are maintained and each do exactly one job.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"

# bcrypt silently ignores bytes beyond 72 - reject longer passwords explicitly
# instead of letting them be truncated without the user knowing.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > _MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {_MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(*, subject: str, expires_delta: timedelta) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """Return the subject (user id) encoded in a valid, unexpired token.

    Raises `jwt.PyJWTError` (or a subclass, e.g. `ExpiredSignatureError`) for
    any invalid/expired token - callers translate that into a 401.
    """
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    return str(payload["sub"])
