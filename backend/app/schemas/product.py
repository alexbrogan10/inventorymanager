from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryRead
from app.schemas.supplier import SupplierRead


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: int
    supplier_id: int
    purchase_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    selling_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    current_quantity: int = Field(default=0, ge=0)
    minimum_quantity: int = Field(default=0, ge=0)
    maximum_quantity: int | None = Field(default=None, ge=0)
    warehouse_location: str | None = Field(default=None, max_length=255)
    unit_type: str = Field(default="each", min_length=1, max_length=50)

    @model_validator(mode="after")
    def check_maximum_is_at_least_minimum(self) -> Self:
        if self.maximum_quantity is not None and self.maximum_quantity < self.minimum_quantity:
            raise ValueError("maximum_quantity must be greater than or equal to minimum_quantity.")
        return self


# Same shape as ProductCreate - see CategoryUpdate for why PUT is a full
# replacement here rather than a partial PATCH-style update. Image upload is
# a separate endpoint (multipart, not JSON) so image_url isn't settable here.
class ProductUpdate(ProductCreate):
    pass


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    barcode: str | None
    name: str
    description: str | None
    category_id: int
    supplier_id: int
    category: CategoryRead
    supplier: SupplierRead
    purchase_price: Decimal
    selling_price: Decimal
    current_quantity: int
    minimum_quantity: int
    maximum_quantity: int | None
    warehouse_location: str | None
    unit_type: str
    image_url: str | None
    created_at: datetime
    updated_at: datetime
