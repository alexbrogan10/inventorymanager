from decimal import Decimal
from typing import Any, Literal, Protocol

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models.category import Category
from app.models.inventory_level import InventoryLevel
from app.models.product import Product
from app.models.supplier import Supplier

# Every read query eager-loads category/supplier (Milestone 3's entities) so
# ProductRead's nested CategoryRead/SupplierRead never trigger a lazy-load
# per row.
_EAGER_LOAD_OPTIONS = (joinedload(Product.category), joinedload(Product.supplier))

StockStatusFilter = Literal["in_stock", "low_stock", "out_of_stock"]


class AbstractProductRepository(Protocol):
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
    ) -> tuple[list[Product], int]: ...

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
        minimum_quantity: int,
        maximum_quantity: int | None,
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
        minimum_quantity: int,
        maximum_quantity: int | None,
        unit_type: str,
    ) -> Product: ...

    def delete(self, product: Product) -> None: ...

    def set_image_url(self, product: Product, image_url: str) -> Product: ...


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

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
    ) -> tuple[list[Product], int]:
        # Grouped once, then outer-joined - a product with no inventory rows
        # at all still gets a row here (coalesced to 0), and a product with
        # rows across several warehouses collapses to one summed row, so
        # joining it to Product below can never fan out a Product into
        # duplicate rows.
        total_quantity_subq = (
            select(
                InventoryLevel.product_id.label("product_id"),
                func.sum(InventoryLevel.quantity).label("total_quantity"),
            )
            .group_by(InventoryLevel.product_id)
            .subquery()
        )
        total_quantity_expr = func.coalesce(total_quantity_subq.c.total_quantity, 0)

        conditions = []
        if query:
            pattern = f"%{query}%"
            conditions.append(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.barcode.ilike(pattern),
                    Category.name.ilike(pattern),
                    Supplier.company_name.ilike(pattern),
                )
            )
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if supplier_id is not None:
            conditions.append(Product.supplier_id == supplier_id)
        if warehouse_id is not None:
            conditions.append(
                Product.id.in_(
                    select(InventoryLevel.product_id).where(
                        InventoryLevel.warehouse_id == warehouse_id, InventoryLevel.quantity > 0
                    )
                )
            )
        if stock_status == "out_of_stock":
            conditions.append(total_quantity_expr == 0)
        elif stock_status == "low_stock":
            conditions.append(total_quantity_expr > 0)
            conditions.append(total_quantity_expr < Product.minimum_quantity)
        elif stock_status == "in_stock":
            conditions.append(total_quantity_expr >= Product.minimum_quantity)
        if min_quantity is not None:
            conditions.append(total_quantity_expr >= min_quantity)
        if max_quantity is not None:
            conditions.append(total_quantity_expr <= max_quantity)

        # category_id/supplier_id are NOT NULL FKs, so these are plain inner
        # joins - joined explicitly (rather than relying on joinedload) so
        # the search condition above can filter on Category.name/
        # Supplier.company_name; contains_eager then populates
        # Product.category/.supplier from this same join instead of
        # joinedload silently adding a second one.
        def _joined(stmt: Select[Any]) -> Select[Any]:
            return (
                stmt.join(Category, Product.category_id == Category.id)
                .join(Supplier, Product.supplier_id == Supplier.id)
                .outerjoin(total_quantity_subq, total_quantity_subq.c.product_id == Product.id)
                .where(*conditions)
            )

        count_query = _joined(select(func.count(Product.id.distinct())))
        total = self._db.execute(count_query).scalar_one()

        page_query = (
            _joined(select(Product))
            .options(contains_eager(Product.category), contains_eager(Product.supplier))
            .order_by(Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self._db.execute(page_query).unique().scalars())
        return items, total

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
        minimum_quantity: int,
        maximum_quantity: int | None,
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
            minimum_quantity=minimum_quantity,
            maximum_quantity=maximum_quantity,
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
        minimum_quantity: int,
        maximum_quantity: int | None,
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
        product.minimum_quantity = minimum_quantity
        product.maximum_quantity = maximum_quantity
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
