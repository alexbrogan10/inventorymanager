"""Audit record of stock moved between warehouses.

Kept as an append-only log (never updated/deleted) so it can double as the
data source for a future "product movement" report - see docs/ROADMAP.md
Milestone 10.
"""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse


class InventoryTransfer(Base, TimestampMixin):
    __tablename__ = "inventory_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    transferred_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    product: Mapped[Product] = relationship()
    from_warehouse: Mapped[Warehouse] = relationship(foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped[Warehouse] = relationship(foreign_keys=[to_warehouse_id])
    transferred_by: Mapped[User] = relationship()
