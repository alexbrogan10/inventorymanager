from app.core.cache import Cache
from app.models.purchase_order import PurchaseOrder
from app.models.sale import Sale
from app.repositories.dashboard_repository import AbstractDashboardRepository
from app.schemas.dashboard import DashboardSummary, RecentActivityItem, TopSellingProduct

_TOP_SELLERS_LIMIT = 5
_RECENT_ACTIVITY_LIMIT = 10
_CACHE_KEY = "dashboard:summary"


def _sale_activity(sale: Sale) -> RecentActivityItem:
    return RecentActivityItem(
        type="sale",
        id=sale.id,
        timestamp=sale.created_at,
        summary=f"Sale #{sale.id} to {sale.customer_name}",
    )


def _purchase_order_activity(order: PurchaseOrder) -> RecentActivityItem:
    return RecentActivityItem(
        type="purchase_order",
        id=order.id,
        timestamp=order.created_at,
        summary=(
            f"Purchase order #{order.id} from {order.supplier.company_name} ({order.status.value})"
        ),
    )


class DashboardService:
    def __init__(
        self, repository: AbstractDashboardRepository, cache: Cache, cache_ttl_seconds: int
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    def get_summary(self) -> DashboardSummary:
        cached = self._cache.get(_CACHE_KEY)
        if cached is not None:
            return DashboardSummary.model_validate_json(cached)

        summary = self._compute_summary()
        self._cache.set(_CACHE_KEY, summary.model_dump_json(), self._cache_ttl_seconds)
        return summary

    def _compute_summary(self) -> DashboardSummary:
        low_stock_count, out_of_stock_count = self._repository.get_stock_counts()

        top_sellers = [
            TopSellingProduct(
                id=product.id,
                sku=product.sku,
                name=product.name,
                total_quantity_sold=quantity,
                total_revenue=revenue,
            )
            for product, quantity, revenue in self._repository.get_top_selling_products(
                _TOP_SELLERS_LIMIT
            )
        ]

        activity = [
            *(
                _sale_activity(sale)
                for sale in self._repository.get_recent_sales(_RECENT_ACTIVITY_LIMIT)
            ),
            *(
                _purchase_order_activity(order)
                for order in self._repository.get_recent_purchase_orders(_RECENT_ACTIVITY_LIMIT)
            ),
        ]
        activity.sort(key=lambda item: item.timestamp, reverse=True)

        return DashboardSummary(
            inventory_value=self._repository.get_inventory_value(),
            total_products=self._repository.get_total_products(),
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            pending_purchase_orders_count=self._repository.get_pending_purchase_orders_count(),
            top_selling_products=top_sellers,
            recent_activity=activity[:_RECENT_ACTIVITY_LIMIT],
        )
