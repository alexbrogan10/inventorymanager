"""Demand forecasting: trains a Random Forest on daily sales history and
uses it to answer, per product, "how much will sell tomorrow", "when will
we run out", and "how much should we reorder". See
app/ml/model.py and app/ml/features.py for the model/feature-engineering
itself - this module is the business-rule layer on top: what a prediction
means for stock depletion and reorder quantity, and what to do when a
product doesn't have enough history for the model to say anything useful.
"""

import math
from datetime import date, timedelta
from pathlib import Path

from app.ml.features import build_next_day_feature_row, build_training_frame
from app.ml.model import TrainedModel, train
from app.models.product import Product
from app.repositories.forecast_repository import AbstractForecastRepository
from app.schemas.forecast import ProductForecast, TrainingSummary
from app.services.product_service import ProductNotFoundError


class ModelNotTrainedError(Exception):
    """Raised when a prediction is requested before POST /forecasting/train
    has ever been run - training is an explicit action, not something a
    prediction request triggers implicitly on the caller's behalf."""


class ForecastService:
    def __init__(self, repository: AbstractForecastRepository, model_path: Path) -> None:
        self._repository = repository
        self._model_path = model_path

    def train(self) -> TrainingSummary:
        training_frame = build_training_frame(self._repository.get_daily_sales())
        trained_model = train(training_frame)
        trained_model.save(self._model_path)
        return TrainingSummary(
            trained_at=trained_model.trained_at,
            training_row_count=trained_model.training_row_count,
            accuracy=trained_model.accuracy,
            feature_importance=trained_model.feature_importances,
        )

    def predict(self, product_id: int) -> ProductForecast:
        product = self._repository.get_product(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        if not self._model_path.exists():
            raise ModelNotTrainedError()

        trained_model = TrainedModel.load(self._model_path)
        current_quantity = self._repository.get_current_quantity(product_id)
        history = self._repository.get_daily_sales_for_product(product_id)
        feature_row = build_next_day_feature_row(product_id, history)

        if feature_row is None:
            return self._fallback_forecast(product, current_quantity, trained_model)

        predicted_daily_demand, confidence = trained_model.predict_with_confidence(feature_row)
        stock_depletion_date = self._depletion_date(current_quantity, predicted_daily_demand)
        reorder_quantity = self._reorder_quantity(
            current_quantity=current_quantity,
            predicted_daily_demand=predicted_daily_demand,
            lead_time_days=product.supplier.lead_time_days,
            minimum_quantity=product.minimum_quantity,
        )

        return ProductForecast(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            current_quantity=current_quantity,
            predicted_daily_demand=round(predicted_daily_demand, 2),
            stock_depletion_date=stock_depletion_date,
            reorder_quantity=reorder_quantity,
            confidence_score=round(confidence, 2),
            has_sufficient_history=True,
            model_accuracy=trained_model.accuracy,
            model_trained_at=trained_model.trained_at,
            feature_importance=trained_model.feature_importances,
        )

    def _fallback_forecast(
        self, product: Product, current_quantity: int, trained_model: TrainedModel
    ) -> ProductForecast:
        """A product with under a week of continuous sales history can't
        get a meaningful lag/rolling-window prediction - fall back to the
        simple "top up to minimum_quantity" policy the rest of the app
        already uses for low-stock, rather than reporting a model opinion
        the model has no real basis for forming."""
        reorder_quantity = max(0, product.minimum_quantity - current_quantity)
        return ProductForecast(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            current_quantity=current_quantity,
            predicted_daily_demand=0.0,
            stock_depletion_date=None,
            reorder_quantity=reorder_quantity,
            confidence_score=0.0,
            has_sufficient_history=False,
            model_accuracy=trained_model.accuracy,
            model_trained_at=trained_model.trained_at,
            feature_importance=trained_model.feature_importances,
        )

    @staticmethod
    def _depletion_date(current_quantity: int, predicted_daily_demand: float) -> date | None:
        if predicted_daily_demand <= 0:
            return None
        days_remaining = math.floor(current_quantity / predicted_daily_demand)
        return date.today() + timedelta(days=days_remaining)

    @staticmethod
    def _reorder_quantity(
        *,
        current_quantity: int,
        predicted_daily_demand: float,
        lead_time_days: int,
        minimum_quantity: int,
    ) -> int:
        """Enough to cover predicted demand during the supplier's lead
        time, plus the product's own minimum_quantity as a safety buffer
        for once that lead time has passed - reusing minimum_quantity as
        the safety-stock figure keeps one definition of "how much buffer
        is enough" instead of this feature inventing a second one."""
        demand_during_lead_time = predicted_daily_demand * lead_time_days
        target_stock = demand_during_lead_time + minimum_quantity
        return max(0, round(target_stock - current_quantity))
