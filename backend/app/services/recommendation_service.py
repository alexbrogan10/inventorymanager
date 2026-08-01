"""Smart Recommendations: four independent, catalog-wide views built on top
of Milestone 12's forecasting - reorder suggestions reuse
ForecastService.predict()'s depletion-date/reorder-quantity logic directly,
so there's one definition of "how much to reorder" shared between a
single-product forecast and this catalog-wide scan. The other three
categories (overstock, slow-moving, seasonal trends) are plain aggregations
over sales history and don't need the trained model at all - so a missing
or stale model degrades this report instead of breaking it.
"""

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Literal

from app.models.product import Product
from app.repositories.forecast_repository import AbstractForecastRepository
from app.schemas.recommendations import (
    OverstockWarning,
    RecommendationsReport,
    ReorderSuggestion,
    SeasonalTrend,
    SlowMovingProduct,
)
from app.services.forecast_service import ForecastService

# A product's stock lasting longer than this at its recent sales pace is
# flagged as overstock - a generous threshold (half a year) so this fires
# on genuine excess, not just healthy buffer stock.
_OVERSTOCK_DAYS_OF_SUPPLY_THRESHOLD = 180
_RECENT_SALES_WINDOW_DAYS = 60
# Below this many distinct sale-days, a weekend/weekday split would be
# comparing a handful of data points - not enough to call it a pattern.
_MIN_SALE_DAYS_FOR_SEASONALITY = 14
_WEEKEND_SPIKE_RATIO = 1.5
_WEEKDAY_LIGHT_RATIO = 1 / _WEEKEND_SPIKE_RATIO


class RecommendationService:
    def __init__(
        self,
        repository: AbstractForecastRepository,
        forecast_service: ForecastService,
        model_path: Path,
    ) -> None:
        self._repository = repository
        self._forecast_service = forecast_service
        self._model_path = model_path

    def list_recommendations(self) -> RecommendationsReport:
        products_with_quantity = self._repository.list_products_with_quantity()
        sales_by_product: dict[int, list[tuple[date, int]]] = defaultdict(list)
        for product_id, sale_date, quantity in self._repository.get_daily_sales():
            sales_by_product[product_id].append((sale_date, quantity))

        model_trained = self._model_path.exists()
        reorder_suggestions = (
            self._reorder_suggestions(products_with_quantity) if model_trained else []
        )

        return RecommendationsReport(
            model_trained=model_trained,
            reorder_suggestions=reorder_suggestions,
            overstock_warnings=self._overstock_warnings(products_with_quantity, sales_by_product),
            slow_moving_products=self._slow_moving_products(
                products_with_quantity, sales_by_product
            ),
            seasonal_trends=self._seasonal_trends(products_with_quantity, sales_by_product),
        )

    def _reorder_suggestions(
        self, products_with_quantity: list[tuple[Product, int]]
    ) -> list[ReorderSuggestion]:
        suggestions = []
        for product, _quantity in products_with_quantity:
            forecast = self._forecast_service.predict(product.id)
            if forecast.reorder_quantity <= 0:
                continue
            days_until_depletion = (
                (forecast.stock_depletion_date - date.today()).days
                if forecast.stock_depletion_date
                else None
            )
            suggestions.append(
                ReorderSuggestion(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    current_quantity=forecast.current_quantity,
                    predicted_daily_demand=forecast.predicted_daily_demand,
                    stock_depletion_date=forecast.stock_depletion_date,
                    days_until_depletion=days_until_depletion,
                    reorder_quantity=forecast.reorder_quantity,
                    confidence_score=forecast.confidence_score,
                )
            )
        # Most urgent (soonest depletion) first; products with no depletion
        # estimate (the fallback, no-history path) sort last.
        suggestions.sort(
            key=lambda s: (s.days_until_depletion is None, s.days_until_depletion or 0)
        )
        return suggestions

    def _overstock_warnings(
        self,
        products_with_quantity: list[tuple[Product, int]],
        sales_by_product: dict[int, list[tuple[date, int]]],
    ) -> list[OverstockWarning]:
        warnings = []
        for product, quantity in products_with_quantity:
            reasons = []
            if product.maximum_quantity is not None and quantity > product.maximum_quantity:
                reasons.append(
                    f"Stock ({quantity}) exceeds maximum_quantity ({product.maximum_quantity})"
                )

            days_of_supply = self._days_of_supply(quantity, sales_by_product.get(product.id, []))
            if days_of_supply is not None and days_of_supply > _OVERSTOCK_DAYS_OF_SUPPLY_THRESHOLD:
                reasons.append(
                    f"At recent sales pace, current stock would last ~{days_of_supply:.0f} days"
                )

            if reasons:
                warnings.append(
                    OverstockWarning(
                        product_id=product.id,
                        sku=product.sku,
                        name=product.name,
                        current_quantity=quantity,
                        maximum_quantity=product.maximum_quantity,
                        days_of_supply=days_of_supply,
                        reasons=reasons,
                    )
                )
        return warnings

    @staticmethod
    def _days_of_supply(quantity: int, history: list[tuple[date, int]]) -> float | None:
        cutoff = date.today() - timedelta(days=_RECENT_SALES_WINDOW_DAYS)
        recent_quantity = sum(q for d, q in history if d >= cutoff)
        if recent_quantity <= 0:
            return None
        recent_daily_rate = recent_quantity / _RECENT_SALES_WINDOW_DAYS
        return quantity / recent_daily_rate

    def _slow_moving_products(
        self,
        products_with_quantity: list[tuple[Product, int]],
        sales_by_product: dict[int, list[tuple[date, int]]],
    ) -> list[SlowMovingProduct]:
        cutoff = date.today() - timedelta(days=_RECENT_SALES_WINDOW_DAYS)
        results = []
        for product, quantity in products_with_quantity:
            if quantity <= 0:
                continue  # nothing on hand to sell through - that's out of stock, not slow-moving
            history = sales_by_product.get(product.id, [])
            recent_quantity = sum(q for d, q in history if d >= cutoff)
            if recent_quantity > 0:
                continue
            last_sale_date = max((d for d, _q in history), default=None)
            days_since_last_sale = (date.today() - last_sale_date).days if last_sale_date else None
            results.append(
                SlowMovingProduct(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    current_quantity=quantity,
                    quantity_sold_last_60_days=0,
                    days_since_last_sale=days_since_last_sale,
                )
            )
        # Never-sold products (None) are the most concerning, listed first;
        # otherwise longest-idle first.
        results.sort(
            key=lambda p: (p.days_since_last_sale is not None, -(p.days_since_last_sale or 0))
        )
        return results

    def _seasonal_trends(
        self,
        products_with_quantity: list[tuple[Product, int]],
        sales_by_product: dict[int, list[tuple[date, int]]],
    ) -> list[SeasonalTrend]:
        trends = []
        for product, _quantity in products_with_quantity:
            history = sales_by_product.get(product.id, [])
            if len(history) < _MIN_SALE_DAYS_FOR_SEASONALITY:
                continue
            weekend_quantities = [q for d, q in history if d.weekday() >= 5]
            weekday_quantities = [q for d, q in history if d.weekday() < 5]
            if not weekend_quantities or not weekday_quantities:
                continue

            weekday_avg = mean(weekday_quantities)
            if weekday_avg == 0:
                continue
            ratio = mean(weekend_quantities) / weekday_avg

            if ratio >= _WEEKEND_SPIKE_RATIO:
                pattern: Literal["weekend_spike", "weekday_light"] = "weekend_spike"
            elif ratio <= _WEEKDAY_LIGHT_RATIO:
                pattern = "weekday_light"
            else:
                continue  # no notable pattern - omit rather than report a "none" row

            trends.append(
                SeasonalTrend(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    pattern=pattern,
                    weekend_to_weekday_ratio=round(ratio, 2),
                )
            )
        return trends
