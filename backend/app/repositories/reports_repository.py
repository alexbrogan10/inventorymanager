from datetime import date, datetime, timedelta
from typing import Protocol

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload

from app.models.inventory_level import InventoryLevel
from app.models.inventory_transfer import InventoryTransfer
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.purchase_order_item import PurchaseOrderItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem


def _range_conditions(
    column: InstrumentedAttribute[datetime], start: date | None, end: date | None
) -> list[ColumnElement[bool]]:
    """`end` is inclusive of the whole day, so the upper bound is exclusive
    of the following day - matches the half-open range every date-range
    filter in this repository uses."""
    conditions: list[ColumnElement[bool]] = []
    if start is not None:
        conditions.append(column >= start)
    if end is not None:
        conditions.append(column < end + timedelta(days=1))
    return conditions


class AbstractReportsRepository(Protocol):
    def get_inventory_valuation(self) -> list[tuple[Product, int]]: ...

    def get_sales(self, start: date | None, end: date | None) -> list[Sale]: ...

    def get_purchase_orders(self, start: date | None, end: date | None) -> list[PurchaseOrder]: ...

    def get_product(self, product_id: int) -> Product | None: ...

    def get_purchase_receipt_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[tuple[PurchaseOrderItem, PurchaseOrder]]: ...

    def get_sale_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[tuple[SaleItem, Sale]]: ...

    def get_transfer_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[InventoryTransfer]: ...

    def get_purchase_orders_with_items(self) -> list[PurchaseOrder]: ...


class ReportsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_inventory_valuation(self) -> list[tuple[Product, int]]:
        total_quantity_subq = (
            select(
                InventoryLevel.product_id.label("product_id"),
                func.sum(InventoryLevel.quantity).label("total_quantity"),
            )
            .group_by(InventoryLevel.product_id)
            .subquery()
        )
        query = (
            select(Product, func.coalesce(total_quantity_subq.c.total_quantity, 0))
            .outerjoin(total_quantity_subq, total_quantity_subq.c.product_id == Product.id)
            .options(joinedload(Product.category), joinedload(Product.supplier))
            .order_by(Product.name)
        )
        return [
            (product, int(quantity)) for product, quantity in self._db.execute(query).unique().all()
        ]

    def get_sales(self, start: date | None, end: date | None) -> list[Sale]:
        query = (
            select(Sale)
            .options(joinedload(Sale.warehouse), joinedload(Sale.sold_by), joinedload(Sale.items))
            .where(*_range_conditions(Sale.created_at, start, end))
            .order_by(Sale.created_at)
        )
        return list(self._db.execute(query).unique().scalars())

    def get_purchase_orders(self, start: date | None, end: date | None) -> list[PurchaseOrder]:
        query = (
            select(PurchaseOrder)
            .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.warehouse))
            .where(*_range_conditions(PurchaseOrder.created_at, start, end))
            .order_by(PurchaseOrder.created_at)
        )
        return list(self._db.execute(query).unique().scalars())

    def get_product(self, product_id: int) -> Product | None:
        query = (
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.supplier))
            .where(Product.id == product_id)
        )
        return self._db.execute(query).unique().scalar_one_or_none()

    def get_purchase_receipt_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[tuple[PurchaseOrderItem, PurchaseOrder]]:
        # PurchaseOrder.updated_at doubles as the receiving timestamp - the
        # status-transition rules never allow a further edit once a PO is
        # RECEIVED, so its last write is guaranteed to be that transition.
        query = (
            select(PurchaseOrderItem, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
            .options(joinedload(PurchaseOrder.warehouse))
            .where(
                PurchaseOrderItem.product_id == product_id,
                PurchaseOrder.status == PurchaseOrderStatus.RECEIVED,
                *_range_conditions(PurchaseOrder.updated_at, start, end),
            )
        )
        return [(item, order) for item, order in self._db.execute(query).unique().all()]

    def get_sale_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[tuple[SaleItem, Sale]]:
        query = (
            select(SaleItem, Sale)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .options(joinedload(Sale.warehouse))
            .where(
                SaleItem.product_id == product_id,
                *_range_conditions(Sale.created_at, start, end),
            )
        )
        return [(item, sale) for item, sale in self._db.execute(query).unique().all()]

    def get_transfer_events(
        self, product_id: int, start: date | None, end: date | None
    ) -> list[InventoryTransfer]:
        query = (
            select(InventoryTransfer)
            .options(
                joinedload(InventoryTransfer.from_warehouse),
                joinedload(InventoryTransfer.to_warehouse),
            )
            .where(
                InventoryTransfer.product_id == product_id,
                *_range_conditions(InventoryTransfer.created_at, start, end),
            )
        )
        return list(self._db.execute(query).unique().scalars())

    def get_purchase_orders_with_items(self) -> list[PurchaseOrder]:
        query = select(PurchaseOrder).options(
            joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.items)
        )
        return list(self._db.execute(query).unique().scalars())
