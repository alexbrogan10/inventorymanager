from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.warehouse import WarehouseRead


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class SaleCreate(BaseModel):
    warehouse_id: int
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    items: list[SaleItemCreate] = Field(min_length=1)


# Deliberately not the full ProductRead - see PurchaseOrderItemProductRead for
# why total_quantity (a virtual attribute the product service attaches, never
# populated on a Product loaded via the sale's own eager-load) is left out.
class SaleItemProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    unit_type: str


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: SaleItemProductRead
    quantity: int
    unit_price: Decimal


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse: WarehouseRead
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    notes: str | None
    sold_by_id: int
    items: list[SaleItemRead]
    created_at: datetime
    updated_at: datetime


class PaginatedSales(BaseModel):
    items: list[SaleRead]
    total: int
    page: int
    page_size: int
