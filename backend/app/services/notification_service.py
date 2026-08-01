"""Turns domain events (a sale deducting stock, a PO being received) into
notification rows. Called from `SaleService`/`PurchaseOrderService`, mirroring
the service-depends-on-service precedent set by `RecommendationService`
depending on `ForecastService` in Milestone 13 - "did something happen worth
telling the user about" is its own concern, distinct from "record the sale"
or "receive the purchase order", even though it has to happen inline with
them to have the data (and the DB session) it needs.

Threshold notifications (low_stock/overstock) fire only on the *crossing*,
not on every check while the condition holds - a product sitting at zero
stock would otherwise get a new notification on every subsequent sale
attempt. Once acknowledged (marked read), the same crossing is free to
notify again should it recur. Anomaly notifications are a one-off "look at
this today" event, so they're capped at one per product per day regardless
of read state instead.
"""

from datetime import date

from app.models.notification import Notification, NotificationSeverity, NotificationType
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.repositories.forecast_repository import AbstractForecastRepository
from app.repositories.notification_repository import AbstractNotificationRepository
from app.schemas.notification import PaginatedNotifications

_ANOMALY_MIN_HISTORY_DAYS = 7
_ANOMALY_SPIKE_MULTIPLIER = 3.0


class NotificationNotFoundError(Exception):
    """Raised when a notification id doesn't exist."""


class NotificationService:
    def __init__(
        self,
        repository: AbstractNotificationRepository,
        forecast_repository: AbstractForecastRepository,
    ) -> None:
        self._repository = repository
        self._forecast_repository = forecast_repository

    def list_notifications(
        self, page: int, page_size: int, unread_only: bool
    ) -> PaginatedNotifications:
        items, total = self._repository.list_paginated(
            page=page, page_size=page_size, unread_only=unread_only
        )
        return PaginatedNotifications(items=items, total=total, page=page, page_size=page_size)

    def unread_count(self) -> int:
        return self._repository.count_unread()

    def mark_read(self, notification_id: int) -> Notification:
        notification = self._repository.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(notification_id)
        return self._repository.mark_read(notification)

    def mark_all_read(self) -> int:
        return self._repository.mark_all_read()

    def check_for_low_stock(
        self, product: Product, previous_quantity: int, new_quantity: int
    ) -> Notification | None:
        threshold = product.minimum_quantity
        if threshold <= 0:
            return None
        if not (previous_quantity >= threshold > new_quantity):
            return None
        if self._repository.has_unread_of_type(NotificationType.LOW_STOCK, product.id):
            return None

        severity = (
            NotificationSeverity.CRITICAL if new_quantity <= 0 else NotificationSeverity.WARNING
        )
        return self._repository.create(
            type=NotificationType.LOW_STOCK,
            severity=severity,
            title=f"Low stock: {product.name}",
            message=(
                f"{product.name} ({product.sku}) has dropped to {new_quantity} units, "
                f"below the minimum of {threshold}."
            ),
            product_id=product.id,
            purchase_order_id=None,
        )

    def check_for_overstock(
        self, product: Product, previous_quantity: int, new_quantity: int
    ) -> Notification | None:
        threshold = product.maximum_quantity
        if threshold is None:
            return None
        if not (previous_quantity <= threshold < new_quantity):
            return None
        if self._repository.has_unread_of_type(NotificationType.OVERSTOCK, product.id):
            return None

        return self._repository.create(
            type=NotificationType.OVERSTOCK,
            severity=NotificationSeverity.WARNING,
            title=f"Overstock: {product.name}",
            message=(
                f"{product.name} ({product.sku}) is now at {new_quantity} units, "
                f"above the maximum of {threshold}."
            ),
            product_id=product.id,
            purchase_order_id=None,
        )

    def notify_order_arrived(self, purchase_order: PurchaseOrder) -> Notification:
        return self._repository.create(
            type=NotificationType.ORDER_ARRIVED,
            severity=NotificationSeverity.INFO,
            title=f"Order #{purchase_order.id} received",
            message=(
                f"Purchase order #{purchase_order.id} from {purchase_order.supplier.company_name} "
                f"has been received into {purchase_order.warehouse.name}."
            ),
            product_id=None,
            purchase_order_id=purchase_order.id,
        )

    def check_for_sale_anomaly(self, product: Product, sale_date: date) -> Notification | None:
        """Flags unusually high demand for a product on the given day,
        compared to its own recent history - reuses the same daily-sales
        query the forecasting/recommendations features already rely on
        rather than introducing a second data-access path for "sales by
        day". Only days with at least one sale count as history (matching
        the slow-moving/seasonal-trend conventions from Milestone 13), so
        the average is "typical demand on a day this product sells", not
        diluted by silent calendar days."""
        daily_sales = self._forecast_repository.get_daily_sales_for_product(product.id)
        today_total = next((qty for day, qty in daily_sales if day == sale_date), 0)
        history = [qty for day, qty in daily_sales if day != sale_date]

        if len(history) < _ANOMALY_MIN_HISTORY_DAYS:
            return None

        average = sum(history) / len(history)
        if average <= 0 or today_total < average * _ANOMALY_SPIKE_MULTIPLIER:
            return None
        if self._repository.has_notification_today(NotificationType.ANOMALY, product.id, sale_date):
            return None

        return self._repository.create(
            type=NotificationType.ANOMALY,
            severity=NotificationSeverity.INFO,
            title=f"Unusual demand: {product.name}",
            message=(
                f"{product.name} ({product.sku}) sold {today_total} units today, "
                f"versus a typical {average:.1f}."
            ),
            product_id=product.id,
            purchase_order_id=None,
        )
