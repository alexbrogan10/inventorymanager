from app.models.sale import Sale
from app.repositories.inventory_repository import AbstractInventoryRepository
from app.repositories.product_repository import AbstractProductRepository
from app.repositories.sale_repository import AbstractSaleRepository, SaleItemInput
from app.repositories.warehouse_repository import AbstractWarehouseRepository
from app.schemas.sale import SaleCreate


class SaleNotFoundError(Exception):
    """Raised when a sale id doesn't exist."""


class InvalidWarehouseError(Exception):
    """Raised when warehouse_id doesn't reference an existing warehouse."""


class InvalidProductError(Exception):
    """Raised when a line item's product_id doesn't reference an existing product."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} does not exist.")


class InsufficientStockError(Exception):
    """Raised when a sale requests more of a product than is available at
    the sale's warehouse."""

    def __init__(self, product_id: int, available: int, requested: int) -> None:
        self.product_id = product_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"Product {product_id}: requested {requested}, only {available} available."
        )


class SaleService:
    def __init__(
        self,
        repository: AbstractSaleRepository,
        warehouses: AbstractWarehouseRepository,
        products: AbstractProductRepository,
        inventory: AbstractInventoryRepository,
    ) -> None:
        self._repository = repository
        self._warehouses = warehouses
        self._products = products
        self._inventory = inventory

    def list_all(self) -> list[Sale]:
        return self._repository.list_all()

    def get(self, sale_id: int) -> Sale:
        sale = self._repository.get_by_id(sale_id)
        if sale is None:
            raise SaleNotFoundError(sale_id)
        return sale

    def create(self, sale_in: SaleCreate, sold_by_id: int) -> Sale:
        if self._warehouses.get_by_id(sale_in.warehouse_id) is None:
            raise InvalidWarehouseError(sale_in.warehouse_id)

        # Aggregate requested quantity per product first, in case the same
        # product appears on more than one line - validating and deducting
        # line-by-line against a snapshot read at the start of each line
        # would under-count a repeated product and allow overselling it.
        requested_by_product: dict[int, int] = {}
        for item in sale_in.items:
            if self._products.get_by_id(item.product_id) is None:
                raise InvalidProductError(item.product_id)
            requested_by_product[item.product_id] = (
                requested_by_product.get(item.product_id, 0) + item.quantity
            )

        # Validate every product has enough stock before deducting any of
        # them - InventoryRepository.set_level commits immediately, so
        # deducting while validation could still fail partway through would
        # leave a partial, inconsistent deduction committed.
        for product_id, quantity in requested_by_product.items():
            level = self._inventory.get_level(product_id, sale_in.warehouse_id)
            available = level.quantity if level is not None else 0
            if available < quantity:
                raise InsufficientStockError(product_id, available, quantity)

        for product_id, quantity in requested_by_product.items():
            level = self._inventory.get_level(product_id, sale_in.warehouse_id)
            available = level.quantity if level is not None else 0
            self._inventory.set_level(product_id, sale_in.warehouse_id, available - quantity)

        items: list[SaleItemInput] = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in sale_in.items
        ]
        return self._repository.create(
            warehouse_id=sale_in.warehouse_id,
            customer_name=sale_in.customer_name,
            customer_email=sale_in.customer_email,
            customer_phone=sale_in.customer_phone,
            notes=sale_in.notes,
            sold_by_id=sold_by_id,
            items=items,
        )
