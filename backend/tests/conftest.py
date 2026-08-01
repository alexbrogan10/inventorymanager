from collections.abc import Callable, Iterator

import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.user import User, UserRole


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """A dedicated `inventory_test` database, with its schema recreated once
    per test run so it always matches the current models exactly - see
    docs/ARCHITECTURE.md's testing strategy for why this is a separate
    database from the one the app uses in dev.
    """
    test_engine = create_engine(get_settings().test_database_url)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """Each test runs inside its own transaction, rolled back afterward, so
    tests never see each other's data. `join_transaction_mode="create_savepoint"`
    lets application code call `session.commit()` (as the repositories do)
    without ending the outer transaction this fixture rolls back.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def _get_db_override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def redis_client() -> Iterator[redis.Redis]:
    """A dedicated logical DB (`test_redis_url`, DB 1) separate from the one
    dev/prod use (DB 0) - flushing is always safe for a pure cache, but a
    separate DB means a test run never race-invalidates a dev cache running
    against the same Redis instance."""
    client = redis.Redis.from_url(get_settings().test_redis_url, decode_responses=True)
    client.flushdb()
    yield client
    client.flushdb()
    client.close()


@pytest.fixture
def auth_token_for(client: TestClient, db_session: Session) -> Callable[..., str]:
    """Creates a user with a given role directly in the DB (bypassing
    public registration, which can only ever create EMPLOYEE accounts - see
    app/services/auth_service.py) and returns a valid access token for them,
    for exercising RBAC-gated endpoints at each role.
    """

    def _make(
        role: UserRole = UserRole.EMPLOYEE,
        email: str = "test.user@example.com",
        password: str = "hunter22",
    ) -> str:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test User",
            role=role,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        return str(response.json()["access_token"])

    return _make
