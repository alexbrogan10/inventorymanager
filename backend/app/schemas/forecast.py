from datetime import date, datetime

from pydantic import BaseModel


class TrainingSummary(BaseModel):
    trained_at: datetime
    training_row_count: int
    accuracy: float | None
    feature_importance: dict[str, float]


class ProductForecast(BaseModel):
    product_id: int
    sku: str
    name: str
    current_quantity: int
    predicted_daily_demand: float
    stock_depletion_date: date | None
    reorder_quantity: int
    confidence_score: float
    # False when the product has under a week of continuous sales history -
    # predicted_daily_demand/confidence_score are then 0 and
    # reorder_quantity falls back to a simple top-up-to-minimum policy
    # instead of a number the model has no real basis for.
    has_sufficient_history: bool
    model_accuracy: float | None
    model_trained_at: datetime
    feature_importance: dict[str, float]
