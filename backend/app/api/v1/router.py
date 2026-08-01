"""Aggregates all v1 endpoint routers into a single router.

Later milestones add one `include_router(...)` line per feature (products,
suppliers, sales, ...) - `main.py` never needs to change.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    dashboard,
    health,
    product_import,
    products,
    purchase_orders,
    reports,
    sales,
    suppliers,
    warehouses,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(suppliers.router)
api_router.include_router(warehouses.router)
# product_import is registered before products so its more specific
# "/products/import..." paths are matched first, even though none of
# products.py's current routes actually overlap with them.
api_router.include_router(product_import.router)
api_router.include_router(products.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(sales.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
