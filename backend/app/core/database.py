"""SQLAlchemy engine/session setup and the `get_db` FastAPI dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """Yield a database session for the duration of a request.

    Used via FastAPI's `Depends(get_db)`, which guarantees the session is
    closed after the request regardless of success or failure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
