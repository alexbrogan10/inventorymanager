"""Aggregates all v1 endpoint routers into a single router.

Later milestones add one `include_router(...)` line per feature (products,
suppliers, sales, ...) - `main.py` never needs to change.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, health, products, suppliers, warehouses

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(suppliers.router)
api_router.include_router(warehouses.router)
api_router.include_router(products.router)
