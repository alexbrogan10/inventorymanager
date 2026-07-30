from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product

# Every read query eager-loads category/supplier (Milestone 3's entities) so
# ProductRead's nested CategoryRead/SupplierRead never trigger a lazy-load
# per row.
_EAGER_LOAD_OPTIONS = (joinedload(Product.category), joinedload(Product.supplier))


class AbstractProductRepository(Protocol):
    def list_all(self) -> list[Product]: ...

    def get_by_id(self, product_id: int) -> Product | None: ...

    def get_by_sku(self, sku: str) -> Product | None: ...

    def get_by_barcode(self, barcode: str) -> Product | None: ...

    def create(
        self,
        *,
        sku: str,
        barcode: str | None,
        name: str,
        description: str | None,
        category_id: int,
        supplier_id: int,
        purchase_price: Decimal,
        selling_price: Decimal,
        current_quantity: int,
        minimum_quantity: int,
        maximum_quantity: int | None,
        warehouse_location: str | None,
        unit_type: str,
    ) -> Product: ...

    def update(
        self,
        product: Product,
        *,
        sku: str,
        barcode: str | None,
        name: str,
        description: str | None,
        category_id: int,
        supplier_id: int,
        purchase_price: Decimal,
        selling_price: Decimal,
        current_quantity: int,
        minimum_quantity: int,
        maximum_quantity: int | None,
        warehouse_location: str | None,
        unit_type: str,
    ) -> Product: ...

    def delete(self, product: Product) -> None: ...

    def set_image_url(self, product: Product, image_url: str) -> Product: ...


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Product]:
        query = select(Product).options(*_EAGER_LOAD_OPTIONS).order_by(Product.name)
        return list(self._db.execute(query).scalars())

    def get_by_id(self, product_id: int) -> Product | None:
        query = select(Product).options(*_EAGER_LOAD_OPTIONS).where(Product.id == product_id)
        return self._db.execute(query).scalar_one_or_none()

    def get_by_sku(self, sku: str) -> Product | None:
        return self._db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()

    def get_by_barcode(self, barcode: str) -> Product | None:
        return self._db.execute(
            select(Product).where(Product.barcode == barcode)
        ).scalar_one_or_none()

    def _reload(self, product_id: int) -> Product:
        """Re-fetch with category/supplier eager-loaded after an insert/update
        built off a plain (non-eager-loaded) Product instance."""
        product = self.get_by_id(product_id)
        assert product is not None  # just committed; must exist
        return product

    def create(
        self,
        *,
        sku: str,
        barcode: str | None,
        name: str,
        description: str | None,
        category_id: int,
        supplier_id: int,
        purchase_price: Decimal,
        selling_price: Decimal,
        current_quantity: int,
        minimum_quantity: int,
        maximum_quantity: int | None,
        warehouse_location: str | None,
        unit_type: str,
    ) -> Product:
        product = Product(
            sku=sku,
            barcode=barcode,
            name=name,
            description=description,
            category_id=category_id,
            supplier_id=supplier_id,
            purchase_price=purchase_price,
            selling_price=selling_price,
            current_quantity=current_quantity,
            minimum_quantity=minimum_quantity,
            maximum_quantity=maximum_quantity,
            warehouse_location=warehouse_location,
            unit_type=unit_type,
        )
        self._db.add(product)
        self._db.commit()
        return self._reload(product.id)

    def update(
        self,
        product: Product,
        *,
        sku: str,
        barcode: str | None,
        name: str,
        description: str | None,
        category_id: int,
        supplier_id: int,
        purchase_price: Decimal,
        selling_price: Decimal,
        current_quantity: int,
        minimum_quantity: int,
        maximum_quantity: int | None,
        warehouse_location: str | None,
        unit_type: str,
    ) -> Product:
        product.sku = sku
        product.barcode = barcode
        product.name = name
        product.description = description
        product.category_id = category_id
        product.supplier_id = supplier_id
        product.purchase_price = purchase_price
        product.selling_price = selling_price
        product.current_quantity = current_quantity
        product.minimum_quantity = minimum_quantity
        product.maximum_quantity = maximum_quantity
        product.warehouse_location = warehouse_location
        product.unit_type = unit_type
        self._db.commit()
        return self._reload(product.id)

    def delete(self, product: Product) -> None:
        self._db.delete(product)
        self._db.commit()

    def set_image_url(self, product: Product, image_url: str) -> Product:
        product.image_url = image_url
        self._db.commit()
        return self._reload(product.id)
