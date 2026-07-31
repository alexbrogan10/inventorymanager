"""The product catalog.

Stock quantity moved out of this table in Milestone 5: `current_quantity`
and `warehouse_location` implied a single location, which stopped being true
once multiple warehouses existed. Actual stock now lives in
`InventoryLevel` (one row per product/warehouse pair) - see that module.
`minimum_quantity`/`maximum_quantity` stay here since reorder policy is a
property of the product, not of any one warehouse.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.category import Category
from app.models.supplier import Supplier


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, default=None)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    category: Mapped[Category] = relationship()
    supplier: Mapped[Supplier] = relationship()

    purchase_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    minimum_quantity: Mapped[int] = mapped_column(default=0)
    maximum_quantity: Mapped[int | None] = mapped_column(default=None)

    unit_type: Mapped[str] = mapped_column(String(50), default="each")

    image_url: Mapped[str | None] = mapped_column(String(512), default=None)

    if TYPE_CHECKING:
        # Not a mapped column - the repository attaches this after a separate
        # aggregate query over InventoryLevel (SUM(quantity) across
        # warehouses). Declared here only so ProductRead's from_attributes
        # validation and mypy both see it as a real attribute.
        total_quantity: int
