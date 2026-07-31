"""SQLAlchemy ORM models.

Every model module is imported here so that `Base.metadata` is fully
populated for Alembic's autogenerate support.
"""

from app.models.base import Base
from app.models.category import Category
from app.models.inventory_level import InventoryLevel
from app.models.inventory_transfer import InventoryTransfer
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.purchase_order_item import PurchaseOrderItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse

__all__ = [
    "Base",
    "Category",
    "InventoryLevel",
    "InventoryTransfer",
    "Product",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseOrderStatus",
    "Sale",
    "SaleItem",
    "Supplier",
    "User",
    "UserRole",
    "Warehouse",
]
