from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory_level import InventoryLevel
from app.models.inventory_transfer import InventoryTransfer


class AbstractInventoryRepository(Protocol):
    def get_level(self, product_id: int, warehouse_id: int) -> InventoryLevel | None: ...

    def list_for_product(self, product_id: int) -> list[InventoryLevel]: ...

    def set_level(self, product_id: int, warehouse_id: int, quantity: int) -> InventoryLevel: ...

    def get_totals_for_products(self, product_ids: list[int]) -> dict[int, int]: ...

    def create_transfer(
        self,
        *,
        product_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: int,
        transferred_by_id: int,
    ) -> InventoryTransfer: ...


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_level(self, product_id: int, warehouse_id: int) -> InventoryLevel | None:
        return self._db.execute(
            select(InventoryLevel).where(
                InventoryLevel.product_id == product_id,
                InventoryLevel.warehouse_id == warehouse_id,
            )
        ).scalar_one_or_none()

    def list_for_product(self, product_id: int) -> list[InventoryLevel]:
        query = (
            select(InventoryLevel)
            .options(joinedload(InventoryLevel.warehouse))
            .where(InventoryLevel.product_id == product_id)
            .join(InventoryLevel.warehouse)
            .order_by(InventoryLevel.warehouse_id)
        )
        return list(self._db.execute(query).scalars())

    def set_level(self, product_id: int, warehouse_id: int, quantity: int) -> InventoryLevel:
        level = self.get_level(product_id, warehouse_id)
        if level is None:
            level = InventoryLevel(
                product_id=product_id, warehouse_id=warehouse_id, quantity=quantity
            )
            self._db.add(level)
        else:
            level.quantity = quantity
        self._db.commit()
        self._db.refresh(level)
        return level

    def get_totals_for_products(self, product_ids: list[int]) -> dict[int, int]:
        if not product_ids:
            return {}
        query = (
            select(InventoryLevel.product_id, func.sum(InventoryLevel.quantity))
            .where(InventoryLevel.product_id.in_(product_ids))
            .group_by(InventoryLevel.product_id)
        )
        return {product_id: total for product_id, total in self._db.execute(query).all()}

    def create_transfer(
        self,
        *,
        product_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: int,
        transferred_by_id: int,
    ) -> InventoryTransfer:
        transfer = InventoryTransfer(
            product_id=product_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            quantity=quantity,
            transferred_by_id=transferred_by_id,
        )
        self._db.add(transfer)
        self._db.commit()
        self._db.refresh(transfer)
        return transfer
