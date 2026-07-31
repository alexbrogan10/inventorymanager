from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.repositories.inventory_repository import AbstractInventoryRepository
from app.repositories.product_repository import AbstractProductRepository
from app.repositories.purchase_order_repository import (
    AbstractPurchaseOrderRepository,
    PurchaseOrderItemInput,
)
from app.repositories.supplier_repository import AbstractSupplierRepository
from app.repositories.warehouse_repository import AbstractWarehouseRepository
from app.schemas.purchase_order import PurchaseOrderCreate


class PurchaseOrderNotFoundError(Exception):
    """Raised when a purchase order id doesn't exist."""


class InvalidSupplierError(Exception):
    """Raised when supplier_id doesn't reference an existing supplier."""


class InvalidWarehouseError(Exception):
    """Raised when warehouse_id doesn't reference an existing warehouse."""


class InvalidProductError(Exception):
    """Raised when a line item's product_id doesn't reference an existing product."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} does not exist.")


class InvalidStatusTransitionError(Exception):
    """Raised when an action isn't valid for the purchase order's current status."""

    def __init__(self, current: PurchaseOrderStatus, action: str) -> None:
        self.current = current
        self.action = action
        super().__init__(f"Cannot {action} a purchase order that is {current.value}.")


class PurchaseOrderService:
    def __init__(
        self,
        repository: AbstractPurchaseOrderRepository,
        suppliers: AbstractSupplierRepository,
        warehouses: AbstractWarehouseRepository,
        products: AbstractProductRepository,
        inventory: AbstractInventoryRepository,
    ) -> None:
        self._repository = repository
        self._suppliers = suppliers
        self._warehouses = warehouses
        self._products = products
        self._inventory = inventory

    def list_all(self) -> list[PurchaseOrder]:
        return self._repository.list_all()

    def get(self, purchase_order_id: int) -> PurchaseOrder:
        order = self._repository.get_by_id(purchase_order_id)
        if order is None:
            raise PurchaseOrderNotFoundError(purchase_order_id)
        return order

    def create(self, order_in: PurchaseOrderCreate, created_by_id: int) -> PurchaseOrder:
        if self._suppliers.get_by_id(order_in.supplier_id) is None:
            raise InvalidSupplierError(order_in.supplier_id)
        if self._warehouses.get_by_id(order_in.warehouse_id) is None:
            raise InvalidWarehouseError(order_in.warehouse_id)
        for item in order_in.items:
            if self._products.get_by_id(item.product_id) is None:
                raise InvalidProductError(item.product_id)

        items: list[PurchaseOrderItemInput] = [
            {
                "product_id": item.product_id,
                "quantity_ordered": item.quantity_ordered,
                "unit_cost": item.unit_cost,
            }
            for item in order_in.items
        ]
        return self._repository.create(
            supplier_id=order_in.supplier_id,
            warehouse_id=order_in.warehouse_id,
            expected_delivery_date=order_in.expected_delivery_date,
            notes=order_in.notes,
            created_by_id=created_by_id,
            items=items,
        )

    def ship(self, purchase_order_id: int) -> PurchaseOrder:
        order = self.get(purchase_order_id)
        if order.status != PurchaseOrderStatus.ORDERED:
            raise InvalidStatusTransitionError(order.status, "ship")
        return self._repository.update_status(order, PurchaseOrderStatus.SHIPPED)

    def cancel(self, purchase_order_id: int) -> PurchaseOrder:
        order = self.get(purchase_order_id)
        if order.status not in (PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.SHIPPED):
            raise InvalidStatusTransitionError(order.status, "cancel")
        return self._repository.update_status(order, PurchaseOrderStatus.CANCELLED)

    def receive(self, purchase_order_id: int) -> PurchaseOrder:
        order = self.get(purchase_order_id)
        if order.status != PurchaseOrderStatus.SHIPPED:
            raise InvalidStatusTransitionError(order.status, "receive")

        for item in order.items:
            current = self._inventory.get_level(item.product_id, order.warehouse_id)
            current_quantity = current.quantity if current is not None else 0
            self._inventory.set_level(
                item.product_id, order.warehouse_id, current_quantity + item.quantity_ordered
            )

        return self._repository.mark_received(order)
