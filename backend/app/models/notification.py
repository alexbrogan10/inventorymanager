"""Operational alerts surfaced across the whole system (not per-user - this
is a single-tenant inventory system, so a low-stock alert is relevant to
every user, not just the one who happened to trigger it).

Notifications are created synchronously, inline with the domain event that
caused them (see `SaleService`/`PurchaseOrderService`), rather than via a
background worker or message queue - there's no such infrastructure in this
system, and the events that matter (a sale deducting stock, a PO being
received) already happen inside a request/response cycle with a DB session
open, so creating the row there is the simplest correct place to do it.
"""

import enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder


class NotificationType(enum.StrEnum):
    LOW_STOCK = "low_stock"
    OVERSTOCK = "overstock"
    ORDER_ARRIVED = "order_arrived"
    ANOMALY = "anomaly"


class NotificationSeverity(enum.StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def _enum_values(members: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in members]


# See UserRole in app/models/user.py for why values_callable is required here.
_notification_type_column_type = SqlEnum(
    NotificationType, name="notification_type", native_enum=True, values_callable=_enum_values
)
_notification_severity_column_type = SqlEnum(
    NotificationSeverity,
    name="notification_severity",
    native_enum=True,
    values_callable=_enum_values,
)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[NotificationType] = mapped_column(_notification_type_column_type, index=True)
    severity: Mapped[NotificationSeverity] = mapped_column(_notification_severity_column_type)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(500))

    # Both nullable and independent - a notification links to whichever
    # entity caused it (a product for low_stock/overstock/anomaly, a
    # purchase order for order_arrived), never both.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), index=True, default=None
    )
    purchase_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders.id"), index=True, default=None
    )
    is_read: Mapped[bool] = mapped_column(default=False, index=True)

    product: Mapped[Product | None] = relationship()
    purchase_order: Mapped[PurchaseOrder | None] = relationship()
