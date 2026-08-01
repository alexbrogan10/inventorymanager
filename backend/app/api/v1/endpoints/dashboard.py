"""Dashboard: a single aggregation endpoint, read = any authenticated user.
There is nothing to write here - every field is computed from other
entities, not stored."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.cache import Cache
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    settings = get_settings()
    return DashboardService(
        DashboardRepository(db), Cache(settings.redis_url), settings.dashboard_cache_ttl_seconds
    )


@router.get("/summary", response_model=DashboardSummary, dependencies=[Depends(get_current_user)])
def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    return service.get_summary()
