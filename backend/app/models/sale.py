"""A recorded sale: unlike `PurchaseOrder`, this is a single-step action, not
a multi-stage lifecycle - a sale happens at the point it's recorded, so
creating one immediately deducts inventory (see `SaleService.create`) rather
than moving through separate ordered/shipped/received stages. There is no
status field and no way to edit or delete a sale once recorded; it's a
financial record, not a draft.

Customer info is captured directly on the sale rather than through a
separate `Customer` entity - this system doesn't have customer accounts or
repeat-customer lookups, so a normalized customer table would be unused
structure for the "customer tracking" this milestone actually asks for.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.sale_item import SaleItem
from app.models.user import User
from app.models.warehouse import Warehouse


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    customer_email: Mapped[str | None] = mapped_column(String(255), default=None)
    customer_phone: Mapped[str | None] = mapped_column(String(50), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    sold_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    warehouse: Mapped[Warehouse] = relationship()
    sold_by: Mapped[User] = relationship()
    items: Mapped[list[SaleItem]] = relationship(
        cascade="all, delete-orphan", order_by="SaleItem.id"
    )
