"""One product line on a purchase order.

Quantity received is tracked per line (not just a status flag on the header)
so a partial-receiving history stays representable later, even though
Milestone 6's `PurchaseOrderService.receive` always receives every line in
full in one action.
"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity_ordered: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity_received: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship()
