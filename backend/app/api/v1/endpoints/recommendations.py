"""Smart Recommendations: read = any authenticated user, same as dashboard
and reports - this is a computed view over existing data, not something
that mutates anything, so there's no write-only path here at all.
"""

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.recommendations import RecommendationsReport
from app.services.forecast_service import ForecastService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    model_path = Path(get_settings().ml_model_dir) / "demand_forecast_model.joblib"
    repository = ForecastRepository(db)
    forecast_service = ForecastService(repository, model_path)
    return RecommendationService(repository, forecast_service, model_path)


@router.get("", response_model=RecommendationsReport, dependencies=[Depends(get_current_user)])
def get_recommendations(
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationsReport:
    return service.list_recommendations()
