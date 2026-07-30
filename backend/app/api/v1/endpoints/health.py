"""Liveness and readiness checks.

Split into two endpoints on purpose:
- `/health/live` answers "is the process up?" and must never touch the
  database - it's what an orchestrator restarts the container on.
- `/health/ready` answers "can this instance serve traffic?" and checks the
  database connection - it's what a load balancer/orchestrator uses to decide
  whether to route requests to this instance.
Conflating the two would cause a slow/unavailable database to look like a
crashed process and trigger unnecessary restarts.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any DB failure means "not ready"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not reachable: {exc}",
        ) from exc
    return {"status": "ok"}
