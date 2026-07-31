from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.warehouse import WarehouseRead


class InventoryLevelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse: WarehouseRead
    quantity: int


class SetInventoryLevelRequest(BaseModel):
    quantity: int = Field(ge=0)


class TransferRequest(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def check_different_warehouses(self) -> Self:
        if self.from_warehouse_id == self.to_warehouse_id:
            raise ValueError("from_warehouse_id and to_warehouse_id must be different.")
        return self


class InventoryTransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    from_warehouse: WarehouseRead
    to_warehouse: WarehouseRead
    quantity: int
    created_at: datetime
