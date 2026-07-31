"""Purchase orders: a restocking order placed with a supplier.

Status is a strict lifecycle enforced by `PurchaseOrderService`, not by a
database constraint: ORDERED -> SHIPPED -> RECEIVED is the happy path;
CANCELLED is reachable from ORDERED or SHIPPED but never from RECEIVED,
since receiving has already mutated inventory and is a completed fact.
Receiving a PO adds every line's `quantity_ordered` to `InventoryLevel` at
the PO's `warehouse_id` - see docs/ARCHITECTURE.md, Milestone 6.
"""

import enum
from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.purchase_order_item import PurchaseOrderItem
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse


class PurchaseOrderStatus(enum.StrEnum):
    ORDERED = "ordered"
    SHIPPED = "shipped"
    RECEIVED = "received"
    CANCELLED = "cancelled"


def _status_values(members: type[PurchaseOrderStatus]) -> list[str]:
    return [member.value for member in members]


# See UserRole in app/models/user.py for why values_callable is required here.
_purchase_order_status_column_type = SqlEnum(
    PurchaseOrderStatus,
    name="purchase_order_status",
    native_enum=True,
    values_callable=_status_values,
)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        _purchase_order_status_column_type, default=PurchaseOrderStatus.ORDERED, index=True
    )
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    supplier: Mapped[Supplier] = relationship()
    warehouse: Mapped[Warehouse] = relationship()
    created_by: Mapped[User] = relationship()
    items: Mapped[list[PurchaseOrderItem]] = relationship(
        cascade="all, delete-orphan", order_by="PurchaseOrderItem.id"
    )
