"""Product CRUD, plus a dedicated image-upload endpoint. Same read/write
access split as categories.py and suppliers.py.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.storage import MAX_IMAGE_BYTES, content_type_extension
from app.models.product import Product
from app.models.user import UserRole
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import (
    DuplicateBarcodeError,
    DuplicateSkuError,
    InvalidCategoryError,
    InvalidSupplierError,
    ProductNotFoundError,
    ProductService,
)

router = APIRouter(prefix="/products", tags=["products"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db), CategoryRepository(db), SupplierRepository(db))


def _reference_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidCategoryError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="category_id does not exist."
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="supplier_id does not exist."
    )


@router.get("", response_model=list[ProductRead], dependencies=[Depends(get_current_user)])
def list_products(service: ProductService = Depends(get_product_service)) -> list[Product]:
    return service.list_all()


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
