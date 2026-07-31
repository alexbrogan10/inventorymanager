from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse


class AbstractWarehouseRepository(Protocol):
    def list_all(self) -> list[Warehouse]: ...

    def get_by_id(self, warehouse_id: int) -> Warehouse | None: ...

    def get_by_name(self, name: str) -> Warehouse | None: ...

    def create(self, *, name: str, address: str, notes: str | None) -> Warehouse: ...

    def update(
        self, warehouse: Warehouse, *, name: str, address: str, notes: str | None
    ) -> Warehouse: ...

    def delete(self, warehouse: Warehouse) -> None: ...


class WarehouseRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Warehouse]:
        return list(self._db.execute(select(Warehouse).order_by(Warehouse.name)).scalars())

    def get_by_id(self, warehouse_id: int) -> Warehouse | None:
        return self._db.get(Warehouse, warehouse_id)

    def get_by_name(self, name: str) -> Warehouse | None:
        return self._db.execute(
            select(Warehouse).where(Warehouse.name == name)
        ).scalar_one_or_none()

    def create(self, *, name: str, address: str, notes: str | None) -> Warehouse:
        warehouse = Warehouse(name=name, address=address, notes=notes)
        self._db.add(warehouse)
        self._db.commit()
        self._db.refresh(warehouse)
        return warehouse

    def update(
        self, warehouse: Warehouse, *, name: str, address: str, notes: str | None
    ) -> Warehouse:
        warehouse.name = name
        warehouse.address = address
        warehouse.notes = notes
        self._db.commit()
        self._db.refresh(warehouse)
        return warehouse

    def delete(self, warehouse: Warehouse) -> None:
        self._db.delete(warehouse)
        self._db.commit()
