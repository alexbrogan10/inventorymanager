from datetime import date
from typing import Literal

from pydantic import BaseModel


class ReorderSuggestion(BaseModel):
    product_id: int
    sku: str
    name: str
    current_quantity: int
    predicted_daily_demand: float
    stock_depletion_date: date | None
    days_until_depletion: int | None
    reorder_quantity: int
    confidence_score: float


class OverstockWarning(BaseModel):
    product_id: int
    sku: str
    name: str
    current_quantity: int
    maximum_quantity: int | None
    # None when there's no recent sales pace to estimate a sell-through
    # time from - the "over maximum_quantity" reason can still apply on
    # its own in that case.
    days_of_supply: float | None
    reasons: list[str]


class SlowMovingProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    current_quantity: int
    quantity_sold_last_60_days: int
    # None if the product has never had a recorded sale at all.
    days_since_last_sale: int | None


class SeasonalTrend(BaseModel):
    product_id: int
    sku: str
    name: str
    pattern: Literal["weekend_spike", "weekday_light"]
    weekend_to_weekday_ratio: float


class RecommendationsReport(BaseModel):
    # False when POST /forecasting/train has never been run -
    # reorder_suggestions is then always empty, but the other three
    # categories (which don't depend on the trained model) are still
    # computed - one prerequisite missing shouldn't blank the whole report.
    model_trained: bool
    reorder_suggestions: list[ReorderSuggestion]
    overstock_warnings: list[OverstockWarning]
    slow_moving_products: list[SlowMovingProduct]
    seasonal_trends: list[SeasonalTrend]
