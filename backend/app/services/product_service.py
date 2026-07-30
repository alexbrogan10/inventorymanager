from app.core.storage import save_product_image
from app.models.product import Product
from app.repositories.category_repository import AbstractCategoryRepository
from app.repositories.product_repository import AbstractProductRepository
from app.repositories.supplier_repository import AbstractSupplierRepository
from app.schemas.product import ProductCreate, ProductUpdate


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
    ) -> None:
        self._repository = repository
        self._categories = categories
        self._suppliers = suppliers

    def list_all(self) -> list[Product]:
        return self._repository.list_all()

    def get(self, product_id: int) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

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
        return self._repository.create(**product_in.model_dump())

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
        return self._repository.update(product, **product_in.model_dump())

    def delete(self, product_id: int) -> None:
        self._repository.delete(self.get(product_id))

    def set_product_image(self, product_id: int, contents: bytes, extension: str) -> Product:
        product = self.get(product_id)
        image_url = save_product_image(product_id, contents, extension)
        return self._repository.set_image_url(product, image_url)
