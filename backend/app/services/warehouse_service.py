from app.models.warehouse import Warehouse
from app.repositories.warehouse_repository import AbstractWarehouseRepository
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


class WarehouseNotFoundError(Exception):
    """Raised when a warehouse id doesn't exist."""


class DuplicateWarehouseNameError(Exception):
    """Raised when a warehouse name is already in use by another warehouse."""


class WarehouseService:
    def __init__(self, repository: AbstractWarehouseRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[Warehouse]:
        return self._repository.list_all()

    def get(self, warehouse_id: int) -> Warehouse:
        warehouse = self._repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(warehouse_id)
        return warehouse

    def create(self, warehouse_in: WarehouseCreate) -> Warehouse:
        if self._repository.get_by_name(warehouse_in.name) is not None:
            raise DuplicateWarehouseNameError(warehouse_in.name)
        return self._repository.create(**warehouse_in.model_dump())

    def update(self, warehouse_id: int, warehouse_in: WarehouseUpdate) -> Warehouse:
        warehouse = self.get(warehouse_id)

        existing = self._repository.get_by_name(warehouse_in.name)
        if existing is not None and existing.id != warehouse_id:
            raise DuplicateWarehouseNameError(warehouse_in.name)

        return self._repository.update(warehouse, **warehouse_in.model_dump())

    def delete(self, warehouse_id: int) -> None:
        self._repository.delete(self.get(warehouse_id))
