from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1)
    notes: str | None = None


# Same shape as WarehouseCreate - see CategoryUpdate for why PUT is a full
# replacement here rather than a partial PATCH-style update.
class WarehouseUpdate(WarehouseCreate):
    pass


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
