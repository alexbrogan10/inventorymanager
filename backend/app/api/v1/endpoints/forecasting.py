"""AI demand forecasting. Training is write access (same RBAC as any other
data-mutating action, even though it mutates a model artifact rather than
business data) since it's an explicit, deliberate action, not something a
GET request should trigger implicitly. Predictions are read = any
authenticated user, same as every other read endpoint in the app.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.core.database import get_db
from app.ml.model import InsufficientTrainingDataError
from app.models.user import UserRole
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import ProductForecast, TrainingSummary
from app.services.forecast_service import ForecastService, ModelNotTrainedError
from app.services.product_service import ProductNotFoundError

router = APIRouter(prefix="/forecasting", tags=["forecasting"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_forecast_service(db: Session = Depends(get_db)) -> ForecastService:
    model_path = Path(get_settings().ml_model_dir) / "demand_forecast_model.joblib"
    return ForecastService(ForecastRepository(db), model_path)


@router.post("/train", response_model=TrainingSummary, dependencies=[Depends(_can_write)])
def train_model(service: ForecastService = Depends(get_forecast_service)) -> TrainingSummary:
    try:
        return service.train()
    except InsufficientTrainingDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get(
    "/products/{product_id}/predict",
    response_model=ProductForecast,
    dependencies=[Depends(get_current_user)],
)
def predict_product_demand(
    product_id: int, service: ForecastService = Depends(get_forecast_service)
) -> ProductForecast:
    try:
        return service.predict(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc
    except ModelNotTrainedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The forecasting model has not been trained yet. POST /forecasting/train first.",
        ) from exc
