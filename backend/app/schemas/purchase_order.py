from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase_order import PurchaseOrderStatus
from app.schemas.supplier import SupplierRead
from app.schemas.warehouse import WarehouseRead


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity_ordered: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    expected_delivery_date: date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


# Deliberately not the full ProductRead: a PO line only needs enough to
# identify and display the product, and ProductRead's total_quantity is a
# virtual attribute the product repository attaches - it's never populated on
# a Product loaded here via the purchase order's own eager-load.
class PurchaseOrderItemProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    unit_type: str


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: PurchaseOrderItemProductRead
    quantity_ordered: int
    unit_cost: Decimal
    quantity_received: int


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier: SupplierRead
    warehouse: WarehouseRead
    status: PurchaseOrderStatus
    expected_delivery_date: date | None
    notes: str | None
    created_by_id: int
    items: list[PurchaseOrderItemRead]
    created_at: datetime
    updated_at: datetime
