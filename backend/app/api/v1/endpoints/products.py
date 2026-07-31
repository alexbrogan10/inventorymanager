"""Product CRUD, image upload, and per-warehouse inventory (levels + stock
transfers). Same read/write access split as categories.py and suppliers.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.storage import MAX_IMAGE_BYTES, content_type_extension
from app.models.inventory_level import InventoryLevel
from app.models.product import Product
from app.models.user import User, UserRole
from app.repositories.category_repository import CategoryRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.inventory import InventoryLevelRead, SetInventoryLevelRequest, TransferRequest
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    StockStatus,
)
from app.services.inventory_service import (
    InsufficientStockError,
    InventoryService,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.services.product_service import (
    DuplicateBarcodeError,
    DuplicateSkuError,
    InvalidCategoryError,
    InvalidSupplierError,
    ProductService,
)

router = APIRouter(prefix="/products", tags=["products"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(
        ProductRepository(db),
        CategoryRepository(db),
        SupplierRepository(db),
        InventoryRepository(db),
    )


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    return InventoryService(InventoryRepository(db), ProductRepository(db), WarehouseRepository(db))


def _reference_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidCategoryError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="category_id does not exist."
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="supplier_id does not exist."
    )


@router.get("", response_model=PaginatedProducts, dependencies=[Depends(get_current_user)])
def list_products(
    q: str | None = Query(
        default=None, description="Matches SKU, name, barcode, category, or supplier."
    ),
    category_id: int | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    stock_status: StockStatus | None = None,
    min_quantity: int | None = Query(default=None, ge=0),
    max_quantity: int | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
) -> PaginatedProducts:
    return service.search(
        query=q,
        category_id=category_id,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        stock_status=stock_status.value if stock_status else None,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductRead, dependencies=[Depends(get_current_user)])
def get_product(product_id: int, service: ProductService = Depends(get_product_service)) -> Product:
    try:
        return service.get(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_can_write)],
)
def create_product(
    product_in: ProductCreate, service: ProductService = Depends(get_product_service)
) -> Product:
    try:
        return service.create(product_in)
    except DuplicateSkuError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product with that SKU already exists."
        ) from exc
    except DuplicateBarcodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with that barcode already exists.",
        ) from exc
    except (InvalidCategoryError, InvalidSupplierError) as exc:
        raise _reference_error_response(exc) from exc


@router.put("/{product_id}", response_model=ProductRead, dependencies=[Depends(_can_write)])
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> Product:
    try:
        return service.update(product_id, product_in)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc
    except DuplicateSkuError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product with that SKU already exists."
        ) from exc
    except DuplicateBarcodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with that barcode already exists.",
        ) from exc
    except (InvalidCategoryError, InvalidSupplierError) as exc:
        raise _reference_error_response(exc) from exc


@router.delete(
    "/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_can_write)]
)
def delete_product(product_id: int, service: ProductService = Depends(get_product_service)) -> None:
    try:
        service.delete(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc


@router.post("/{product_id}/image", response_model=ProductRead, dependencies=[Depends(_can_write)])
async def upload_product_image(
    product_id: int,
    file: UploadFile,
    service: ProductService = Depends(get_product_service),
) -> Product:
    extension = content_type_extension(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image must be JPEG, PNG, or WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Image must be {MAX_IMAGE_BYTES // (1024 * 1024)}MB or smaller.",
        )

    try:
        return service.set_product_image(product_id, contents, extension)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc


@router.get(
    "/{product_id}/inventory",
    response_model=list[InventoryLevelRead],
    dependencies=[Depends(get_current_user)],
)
def get_product_inventory(
    product_id: int, service: InventoryService = Depends(get_inventory_service)
) -> list[InventoryLevel]:
    try:
        return service.list_for_product(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc


@router.put(
    "/{product_id}/inventory/{warehouse_id}",
    response_model=list[InventoryLevelRead],
    dependencies=[Depends(_can_write)],
)
def set_product_inventory_level(
    product_id: int,
    warehouse_id: int,
    payload: SetInventoryLevelRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> list[InventoryLevel]:
    try:
        service.set_level(product_id, warehouse_id, payload.quantity)
        return service.list_for_product(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc
    except WarehouseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found."
        ) from exc


@router.post("/{product_id}/transfer", response_model=list[InventoryLevelRead])
def transfer_product_inventory(
    product_id: int,
    payload: TransferRequest,
    current_user: User = Depends(_can_write),
    service: InventoryService = Depends(get_inventory_service),
) -> list[InventoryLevel]:
    try:
        service.transfer(
            product_id,
            payload.from_warehouse_id,
            payload.to_warehouse_id,
            payload.quantity,
            current_user.id,
        )
        return service.list_for_product(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        ) from exc
    except WarehouseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found."
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Only {exc.available} available at the source warehouse, "
                f"requested {exc.requested}."
            ),
        ) from exc
