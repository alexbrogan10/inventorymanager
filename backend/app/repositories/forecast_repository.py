from datetime import date
from typing import Protocol

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory_level import InventoryLevel
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem


class AbstractForecastRepository(Protocol):
    def get_daily_sales(self) -> list[tuple[int, date, int]]: ...

    def get_daily_sales_for_product(self, product_id: int) -> list[tuple[date, int]]: ...

    def get_product(self, product_id: int) -> Product | None: ...

    def get_current_quantity(self, product_id: int) -> int: ...


class ForecastRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_daily_sales(self) -> list[tuple[int, date, int]]:
        """One row per (product, calendar day) that had at least one sale,
        quantity summed across every sale that day - across every product,
        for training. Days with zero sales are NOT included here; filling
        those gaps with zeros so each product gets a continuous daily time
        series is feature engineering, not data access - see
        app/ml/features.py.
        """
        sale_date = cast(Sale.created_at, Date)
        query = (
            select(SaleItem.product_id, sale_date.label("sale_date"), func.sum(SaleItem.quantity))
            .join(Sale, SaleItem.sale_id == Sale.id)
            .group_by(SaleItem.product_id, sale_date)
            .order_by(SaleItem.product_id, sale_date)
        )
        return [
            (product_id, sale_date_value, int(quantity))
            for product_id, sale_date_value, quantity in self._db.execute(query).all()
        ]

    def get_daily_sales_for_product(self, product_id: int) -> list[tuple[date, int]]:
        """Same shape as get_daily_sales, scoped to one product - used at
        prediction time so a single-product forecast doesn't have to pull
        every product's sales history just to look at one."""
        sale_date = cast(Sale.created_at, Date)
        query = (
            select(sale_date.label("sale_date"), func.sum(SaleItem.quantity))
            .join(Sale, SaleItem.sale_id == Sale.id)
            .where(SaleItem.product_id == product_id)
            .group_by(sale_date)
            .order_by(sale_date)
        )
        return [
            (sale_date_value, int(quantity))
            for sale_date_value, quantity in self._db.execute(query).all()
        ]

    def get_product(self, product_id: int) -> Product | None:
        query = (
            select(Product)
            .options(joinedload(Product.supplier), joinedload(Product.category))
            .where(Product.id == product_id)
        )
        return self._db.execute(query).unique().scalar_one_or_none()

    def get_current_quantity(self, product_id: int) -> int:
        query = select(func.coalesce(func.sum(InventoryLevel.quantity), 0)).where(
            InventoryLevel.product_id == product_id
        )
        return self._db.execute(query).scalar_one()
