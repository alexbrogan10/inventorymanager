"""Bulk product import from CSV. Write access only (same RBAC as creating a
single product) - see app/services/product_import_service.py for why each
row goes through the exact same validation a single `POST /products` would.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.export import to_csv_response
from app.models.user import UserRole
from app.repositories.category_repository import CategoryRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.product_import import ProductImportReport
from app.services.product_import_service import MissingColumnsError, ProductImportService
from app.services.product_service import ProductService

router = APIRouter(prefix="/products/import", tags=["product-import"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)

MAX_IMPORT_BYTES = 2 * 1024 * 1024

_TEMPLATE_ROWS = [
    {
        "sku": "WIDGET-001",
        "name": "Blue Widget",
        "category_name": "Electronics",
        "supplier_name": "Acme Supply Co.",
        "purchase_price": "4.50",
        "selling_price": "9.99",
        "barcode": "",
        "description": "A sample product - category_name and supplier_name must "
        "match an existing category/supplier exactly.",
        "minimum_quantity": "10",
        "maximum_quantity": "",
        "unit_type": "each",
    }
]


def get_product_import_service(db: Session = Depends(get_db)) -> ProductImportService:
    return ProductImportService(
        ProductService(
            ProductRepository(db),
            CategoryRepository(db),
            SupplierRepository(db),
            InventoryRepository(db),
        ),
        CategoryRepository(db),
        SupplierRepository(db),
    )


@router.get("/template", dependencies=[Depends(_can_write)])
def get_import_template() -> Response:
    return to_csv_response(_TEMPLATE_ROWS, "product-import-template.csv")


@router.post(
    "",
    response_model=ProductImportReport,
    dependencies=[Depends(_can_write)],
)
async def import_products(
    file: UploadFile,
    service: ProductImportService = Depends(get_product_import_service),
) -> ProductImportReport:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File must be a .csv file."
        )

    contents = await file.read()
    if len(contents) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"File must be {MAX_IMPORT_BYTES // (1024 * 1024)}MB or smaller.",
        )

    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File must be UTF-8 text."
        ) from exc

    try:
        return service.import_csv(text)
    except MissingColumnsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
