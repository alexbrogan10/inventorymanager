"""One product line on a sale.

`unit_price` is a snapshot of the product's selling price at the moment of
sale, not a live reference to `Product.selling_price` - revenue reporting
needs the price the customer actually paid, which shouldn't drift if the
catalog price changes later. Mirrors `PurchaseOrderItem.unit_cost` for the
same reason.
"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product


class SaleItem(Base, TimestampMixin):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    product: Mapped[Product] = relationship()
