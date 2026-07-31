from app.core.storage import save_product_image
from app.models.product import Product
from app.repositories.category_repository import AbstractCategoryRepository
from app.repositories.inventory_repository import AbstractInventoryRepository
from app.repositories.product_repository import AbstractProductRepository, StockStatusFilter
from app.repositories.supplier_repository import AbstractSupplierRepository
from app.schemas.product import PaginatedProducts, ProductCreate, ProductUpdate


class ProductNotFoundError(Exception):
    """Raised when a product id doesn't exist."""


class DuplicateSkuError(Exception):
    """Raised when a SKU is already in use by another product."""


class DuplicateBarcodeError(Exception):
    """Raised when a barcode is already in use by another product."""


class InvalidCategoryError(Exception):
    """Raised when category_id doesn't reference an existing category."""


class InvalidSupplierError(Exception):
    """Raised when supplier_id doesn't reference an existing supplier."""


class ProductService:
    def __init__(
        self,
        repository: AbstractProductRepository,
        categories: AbstractCategoryRepository,
        suppliers: AbstractSupplierRepository,
        inventory: AbstractInventoryRepository,
    ) -> None:
        self._repository = repository
        self._categories = categories
        self._suppliers = suppliers
        self._inventory = inventory

    def _attach_total(self, product: Product) -> Product:
        totals = self._inventory.get_totals_for_products([product.id])
        product.total_quantity = totals.get(product.id, 0)
        return product

    def _attach_totals(self, products: list[Product]) -> list[Product]:
        totals = self._inventory.get_totals_for_products([p.id for p in products])
        for product in products:
            product.total_quantity = totals.get(product.id, 0)
        return products

    def search(
        self,
        *,
        query: str | None,
        category_id: int | None,
        supplier_id: int | None,
        warehouse_id: int | None,
        stock_status: StockStatusFilter | None,
        min_quantity: int | None,
        max_quantity: int | None,
        page: int,
        page_size: int,
    ) -> PaginatedProducts:
        items, total = self._repository.search(
            query=query,
            category_id=category_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            stock_status=stock_status,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            page=page,
            page_size=page_size,
        )
        return PaginatedProducts(
            items=self._attach_totals(items), total=total, page=page, page_size=page_size
        )

    def get(self, product_id: int) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return self._attach_total(product)

    def _validate_references(self, product_in: ProductCreate) -> None:
        if self._categories.get_by_id(product_in.category_id) is None:
            raise InvalidCategoryError(product_in.category_id)
        if self._suppliers.get_by_id(product_in.supplier_id) is None:
            raise InvalidSupplierError(product_in.supplier_id)

    def create(self, product_in: ProductCreate) -> Product:
        if self._repository.get_by_sku(product_in.sku) is not None:
            raise DuplicateSkuError(product_in.sku)
        if (
            product_in.barcode is not None
            and self._repository.get_by_barcode(product_in.barcode) is not None
        ):
            raise DuplicateBarcodeError(product_in.barcode)
        self._validate_references(product_in)
        product = self._repository.create(**product_in.model_dump())
        return self._attach_total(product)

    def update(self, product_id: int, product_in: ProductUpdate) -> Product:
        product = self.get(product_id)

        existing_sku = self._repository.get_by_sku(product_in.sku)
        if existing_sku is not None and existing_sku.id != product_id:
            raise DuplicateSkuError(product_in.sku)

        if product_in.barcode is not None:
            existing_barcode = self._repository.get_by_barcode(product_in.barcode)
            if existing_barcode is not None and existing_barcode.id != product_id:
                raise DuplicateBarcodeError(product_in.barcode)

        self._validate_references(product_in)
        updated = self._repository.update(product, **product_in.model_dump())
        return self._attach_total(updated)

    def delete(self, product_id: int) -> None:
        self._repository.delete(self.get(product_id))

    def set_product_image(self, product_id: int, contents: bytes, extension: str) -> Product:
        product = self.get(product_id)
        image_url = save_product_image(product_id, contents, extension)
        updated = self._repository.set_image_url(product, image_url)
        return self._attach_total(updated)
