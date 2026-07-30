"""The product catalog.

`warehouse_location` and the single `current_quantity` are a deliberately
simple, single-location model of stock for now - Milestone 5 (Warehouses &
Inventory Transfers) introduces a proper `Warehouse` entity and per-warehouse
quantities; this is the incremental step before that.
"""

from decimal import Decimal

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

    current_quantity: Mapped[int] = mapped_column(default=0)
    minimum_quantity: Mapped[int] = mapped_column(default=0)
    maximum_quantity: Mapped[int | None] = mapped_column(default=None)

    warehouse_location: Mapped[str | None] = mapped_column(String(255), default=None)
    unit_type: Mapped[str] = mapped_column(String(50), default="each")

    image_url: Mapped[str | None] = mapped_column(String(512), default=None)
