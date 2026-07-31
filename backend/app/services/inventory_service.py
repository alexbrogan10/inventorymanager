from app.models.inventory_level import InventoryLevel
from app.models.inventory_transfer import InventoryTransfer
from app.repositories.inventory_repository import AbstractInventoryRepository
from app.repositories.product_repository import AbstractProductRepository
from app.repositories.warehouse_repository import AbstractWarehouseRepository
from app.services.product_service import ProductNotFoundError
from app.services.warehouse_service import WarehouseNotFoundError

__all__ = ["ProductNotFoundError", "WarehouseNotFoundError"]  # re-exported for callers' convenience


class InsufficientStockError(Exception):
    """Raised when a transfer requests more than is available at the source
    warehouse."""

    def __init__(self, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(f"Requested {requested}, only {available} available.")


class InventoryService:
    def __init__(
        self,
        repository: AbstractInventoryRepository,
        products: AbstractProductRepository,
        warehouses: AbstractWarehouseRepository,
    ) -> None:
        self._repository = repository
        self._products = products
        self._warehouses = warehouses

    def _require_product(self, product_id: int) -> None:
        if self._products.get_by_id(product_id) is None:
            raise ProductNotFoundError(product_id)

    def _require_warehouse(self, warehouse_id: int) -> None:
        if self._warehouses.get_by_id(warehouse_id) is None:
            raise WarehouseNotFoundError(warehouse_id)

    def list_for_product(self, product_id: int) -> list[InventoryLevel]:
        self._require_product(product_id)
        return self._repository.list_for_product(product_id)

    def set_level(self, product_id: int, warehouse_id: int, quantity: int) -> InventoryLevel:
        self._require_product(product_id)
        self._require_warehouse(warehouse_id)
        return self._repository.set_level(product_id, warehouse_id, quantity)

    def transfer(
        self,
        product_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: int,
        transferred_by_id: int,
    ) -> InventoryTransfer:
        self._require_product(product_id)
        self._require_warehouse(from_warehouse_id)
        self._require_warehouse(to_warehouse_id)

        source = self._repository.get_level(product_id, from_warehouse_id)
        available = source.quantity if source is not None else 0
        if available < quantity:
            raise InsufficientStockError(available, quantity)

        destination = self._repository.get_level(product_id, to_warehouse_id)
        destination_quantity = destination.quantity if destination is not None else 0

        self._repository.set_level(product_id, from_warehouse_id, available - quantity)
        self._repository.set_level(product_id, to_warehouse_id, destination_quantity + quantity)

        return self._repository.create_transfer(
            product_id=product_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            quantity=quantity,
            transferred_by_id=transferred_by_id,
        )
