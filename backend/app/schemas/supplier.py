from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_person: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1)
    lead_time_days: int = Field(ge=0)
    notes: str | None = None


# Same shape as SupplierCreate - see CategoryUpdate for why PUT is a full
# replacement here rather than a partial PATCH-style update.
class SupplierUpdate(SupplierCreate):
    pass


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    contact_person: str
    email: EmailStr
    phone: str
    address: str
    lead_time_days: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
