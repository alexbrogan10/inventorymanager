from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class TopSellingProduct(BaseModel):
    id: int
    sku: str
    name: str
    total_quantity_sold: int
    total_revenue: Decimal


class RecentActivityItem(BaseModel):
    type: Literal["sale", "purchase_order"]
    id: int
    timestamp: datetime
    summary: str


class DashboardSummary(BaseModel):
    inventory_value: Decimal
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    pending_purchase_orders_count: int
    top_selling_products: list[TopSellingProduct]
    recent_activity: list[RecentActivityItem]
