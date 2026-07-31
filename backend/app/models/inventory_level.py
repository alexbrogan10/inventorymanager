"""Per-warehouse stock quantities.

Milestone 4's `Product` had a single flat `current_quantity` (implicitly one
location). This table is what replaces it: one row per (product, warehouse)
pair, so a product's total stock is the sum across its rows here. Products
themselves keep `minimum_quantity`/`maximum_quantity` as a global reorder
policy - those aren't warehouse-specific.
"""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.warehouse import Warehouse


class InventoryLevel(Base, TimestampMixin):
    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship()
    warehouse: Mapped[Warehouse] = relationship()
