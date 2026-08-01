from decimal import Decimal
from typing import Protocol, TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.sale import Sale
from app.models.sale_item import SaleItem


class SaleItemInput(TypedDict):
    product_id: int
    quantity: int
    unit_price: Decimal


# Every read query eager-loads the warehouse/seller plus each line's product,
# so SaleRead's nested schemas never trigger a lazy-load per row.
_EAGER_LOAD_OPTIONS = (
    joinedload(Sale.warehouse),
    joinedload(Sale.sold_by),
    joinedload(Sale.items).joinedload(SaleItem.product),
)


class AbstractSaleRepository(Protocol):
    def list_paginated(self, *, page: int, page_size: int) -> tuple[list[Sale], int]: ...

    def get_by_id(self, sale_id: int) -> Sale | None: ...

    def create(
        self,
        *,
        warehouse_id: int,
        customer_name: str,
        customer_email: str | None,
        customer_phone: str | None,
        notes: str | None,
        sold_by_id: int,
        items: list[SaleItemInput],
    ) -> Sale: ...


class SaleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_paginated(self, *, page: int, page_size: int) -> tuple[list[Sale], int]:
        total = self._db.execute(select(func.count(Sale.id))).scalar_one()
        query = (
            select(Sale)
            .options(*_EAGER_LOAD_OPTIONS)
            .order_by(Sale.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self._db.execute(query).unique().scalars())
        return items, total

    def get_by_id(self, sale_id: int) -> Sale | None:
        query = select(Sale).options(*_EAGER_LOAD_OPTIONS).where(Sale.id == sale_id)
        return self._db.execute(query).unique().scalar_one_or_none()

    def create(
        self,
        *,
        warehouse_id: int,
        customer_name: str,
        customer_email: str | None,
        customer_phone: str | None,
        notes: str | None,
        sold_by_id: int,
        items: list[SaleItemInput],
    ) -> Sale:
        sale = Sale(
            warehouse_id=warehouse_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            notes=notes,
            sold_by_id=sold_by_id,
            items=[SaleItem(**item) for item in items],
        )
        self._db.add(sale)
        self._db.commit()
        self._db.refresh(sale)
        return sale
