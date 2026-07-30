"""Tests for the liveness/readiness endpoints.

Readiness is tested with a fake DB session rather than a real database
connection - Milestone 1 has no models yet, so full database-backed test
fixtures are introduced in Milestone 2 alongside the first ORM model. This
still meaningfully covers the endpoint's branching logic (200 vs. 503).
"""

from typing import Any

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


class _WorkingSession:
    def execute(self, *args: Any, **kwargs: Any) -> None:
        return None


class _BrokenSession:
    def execute(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("connection refused")


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_ok(client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: _WorkingSession()
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200


def test_readiness_db_down(client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 503


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
