from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Base


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
