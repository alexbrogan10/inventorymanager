from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class InventoryValuationRow(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    supplier: str
    total_quantity: int
    purchase_price: Decimal
    selling_price: Decimal
    value_at_cost: Decimal
    potential_revenue: Decimal


class InventoryValuationReport(BaseModel):
    rows: list[InventoryValuationRow]
    total_value_at_cost: Decimal
    total_potential_revenue: Decimal


class SalesHistoryRow(BaseModel):
    sale_id: int
    created_at: datetime
    customer_name: str
    warehouse: str
    sold_by: str
    item_count: int
    total_revenue: Decimal


class SalesHistoryReport(BaseModel):
    rows: list[SalesHistoryRow]
    total_revenue: Decimal


class PurchaseHistoryRow(BaseModel):
    purchase_order_id: int
    created_at: datetime
    supplier: str
    warehouse: str
    status: str
    item_count: int
    total_cost: Decimal


class PurchaseHistoryReport(BaseModel):
    rows: list[PurchaseHistoryRow]
    total_cost: Decimal


# "transfer_in"/"transfer_out" split one InventoryTransfer into two ledger
# rows (one per warehouse side) so quantity_change stays a single signed
# number rather than needing separate from/to columns.
ProductMovementEventType = Literal["purchase_receipt", "sale", "transfer_in", "transfer_out"]


class ProductMovementRow(BaseModel):
    timestamp: datetime
    type: ProductMovementEventType
    product_id: int
    product_sku: str
    product_name: str
    warehouse: str
    quantity_change: int
    reference: str


class ProductMovementReport(BaseModel):
    rows: list[ProductMovementRow]


class SupplierPerformanceRow(BaseModel):
    supplier_id: int
    company_name: str
    total_orders: int
    total_received: int
    total_cancelled: int
    total_spend: Decimal
    average_lead_time_days: float | None
    on_time_rate: float | None


class SupplierPerformanceReport(BaseModel):
    rows: list[SupplierPerformanceRow]


class ReportDateRange(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
