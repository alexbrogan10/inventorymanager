from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory_level import InventoryLevel
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.sale import Sale
from app.models.sale_item import SaleItem


class AbstractDashboardRepository(Protocol):
    def get_inventory_value(self) -> Decimal: ...

    def get_total_products(self) -> int: ...

    def get_stock_counts(self) -> tuple[int, int]: ...

    def get_pending_purchase_orders_count(self) -> int: ...

    def get_top_selling_products(self, limit: int) -> list[tuple[Product, int, Decimal]]: ...

    def get_recent_sales(self, limit: int) -> list[Sale]: ...

    def get_recent_purchase_orders(self, limit: int) -> list[PurchaseOrder]: ...


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_inventory_value(self) -> Decimal:
        """Total value of stock on hand, at cost (quantity * purchase_price)
        summed across every warehouse - the standard inventory valuation
        basis, distinct from potential revenue at selling price."""
        query = (
            select(
                func.coalesce(
                    func.sum(InventoryLevel.quantity * Product.purchase_price), Decimal("0")
                )
            )
            .select_from(InventoryLevel)
            .join(Product, InventoryLevel.product_id == Product.id)
        )
        return Decimal(self._db.execute(query).scalar_one())

    def get_total_products(self) -> int:
        return self._db.execute(select(func.count()).select_from(Product)).scalar_one()

    def get_stock_counts(self) -> tuple[int, int]:
        """Returns (low_stock_count, out_of_stock_count). A product is
        out-of-stock at total_quantity == 0, or low-stock at
        0 < total_quantity < minimum_quantity - the two are mutually
        exclusive so callers can add them without double-counting."""
        query = (
            select(Product.minimum_quantity, func.coalesce(func.sum(InventoryLevel.quantity), 0))
            .select_from(Product)
            .join(InventoryLevel, InventoryLevel.product_id == Product.id, isouter=True)
            .group_by(Product.id, Product.minimum_quantity)
        )
        rows = self._db.execute(query).all()
        out_of_stock = sum(1 for _, total in rows if total == 0)
        low_stock = sum(1 for minimum, total in rows if total > 0 and total < minimum)
        return low_stock, out_of_stock

    def get_pending_purchase_orders_count(self) -> int:
        query = (
            select(func.count())
            .select_from(PurchaseOrder)
            .where(
                PurchaseOrder.status.in_([PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.SHIPPED])
            )
        )
        return self._db.execute(query).scalar_one()

    def get_top_selling_products(self, limit: int) -> list[tuple[Product, int, Decimal]]:
        query = (
            select(
                Product,
                func.sum(SaleItem.quantity),
                func.sum(SaleItem.quantity * SaleItem.unit_price),
            )
            .join(SaleItem, SaleItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.sum(SaleItem.quantity).desc())
            .limit(limit)
        )
        return [
            (product, int(quantity), revenue)
            for product, quantity, revenue in self._db.execute(query).all()
        ]

    def get_recent_sales(self, limit: int) -> list[Sale]:
        query = (
            select(Sale)
            .options(joinedload(Sale.warehouse))
            .order_by(Sale.created_at.desc())
            .limit(limit)
        )
        return list(self._db.execute(query).unique().scalars())

    def get_recent_purchase_orders(self, limit: int) -> list[PurchaseOrder]:
        query = (
            select(PurchaseOrder)
            .options(joinedload(PurchaseOrder.supplier))
            .order_by(PurchaseOrder.created_at.desc())
            .limit(limit)
        )
        return list(self._db.execute(query).unique().scalars())
