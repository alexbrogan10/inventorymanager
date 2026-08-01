from datetime import date
from decimal import Decimal
from typing import Protocol, TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.purchase_order_item import PurchaseOrderItem


class PurchaseOrderItemInput(TypedDict):
    product_id: int
    quantity_ordered: int
    unit_cost: Decimal


# Every read query eager-loads the supplier/warehouse/creator plus each line's
# product, so PurchaseOrderRead's nested schemas never trigger a lazy-load per
# row.
_EAGER_LOAD_OPTIONS = (
    joinedload(PurchaseOrder.supplier),
    joinedload(PurchaseOrder.warehouse),
    joinedload(PurchaseOrder.created_by),
    joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
)


class AbstractPurchaseOrderRepository(Protocol):
    def list_paginated(self, *, page: int, page_size: int) -> tuple[list[PurchaseOrder], int]: ...

    def get_by_id(self, purchase_order_id: int) -> PurchaseOrder | None: ...

    def create(
        self,
        *,
        supplier_id: int,
        warehouse_id: int,
        expected_delivery_date: date | None,
        notes: str | None,
        created_by_id: int,
        items: list[PurchaseOrderItemInput],
    ) -> PurchaseOrder: ...

    def update_status(self, order: PurchaseOrder, status: PurchaseOrderStatus) -> PurchaseOrder: ...

    def mark_received(self, order: PurchaseOrder) -> PurchaseOrder: ...


class PurchaseOrderRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_paginated(self, *, page: int, page_size: int) -> tuple[list[PurchaseOrder], int]:
        total = self._db.execute(select(func.count(PurchaseOrder.id))).scalar_one()
        query = (
            select(PurchaseOrder)
            .options(*_EAGER_LOAD_OPTIONS)
            .order_by(PurchaseOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self._db.execute(query).unique().scalars())
        return items, total

    def get_by_id(self, purchase_order_id: int) -> PurchaseOrder | None:
        query = (
            select(PurchaseOrder)
            .options(*_EAGER_LOAD_OPTIONS)
            .where(PurchaseOrder.id == purchase_order_id)
        )
        return self._db.execute(query).unique().scalar_one_or_none()

    def create(
        self,
        *,
        supplier_id: int,
        warehouse_id: int,
        expected_delivery_date: date | None,
        notes: str | None,
        created_by_id: int,
        items: list[PurchaseOrderItemInput],
    ) -> PurchaseOrder:
        order = PurchaseOrder(
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            expected_delivery_date=expected_delivery_date,
            notes=notes,
            created_by_id=created_by_id,
            items=[PurchaseOrderItem(**item) for item in items],
        )
        self._db.add(order)
        self._db.commit()
        self._db.refresh(order)
        return order

    def update_status(self, order: PurchaseOrder, status: PurchaseOrderStatus) -> PurchaseOrder:
        order.status = status
        self._db.commit()
        self._db.refresh(order)
        return order

    def mark_received(self, order: PurchaseOrder) -> PurchaseOrder:
        for item in order.items:
            item.quantity_received = item.quantity_ordered
        order.status = PurchaseOrderStatus.RECEIVED
        self._db.commit()
        self._db.refresh(order)
        return order
