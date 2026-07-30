from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


# Same shape as CategoryCreate: PUT here means full replacement (every field
# is provided), matching the plain PUT/POST/DELETE API shape in the project
# spec rather than introducing PATCH's partial-update semantics.
class CategoryUpdate(CategoryCreate):
    pass


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
