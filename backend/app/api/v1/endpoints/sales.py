"""Sales: read = any authenticated user, create = manager/admin, same split
as every other business-resource router. There is no PUT/DELETE - a sale is
a financial record recorded at a single point in time (see `Sale`'s
docstring for why it has no status lifecycle either).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.sale import Sale
from app.models.user import User, UserRole
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.sale import SaleCreate, SaleRead
from app.services.sale_service import (
    InsufficientStockError,
    InvalidProductError,
    InvalidWarehouseError,
    SaleNotFoundError,
    SaleService,
)

router = APIRouter(prefix="/sales", tags=["sales"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_sale_service(db: Session = Depends(get_db)) -> SaleService:
    return SaleService(
        SaleRepository(db),
        WarehouseRepository(db),
        ProductRepository(db),
        InventoryRepository(db),
    )


@router.get("", response_model=list[SaleRead], dependencies=[Depends(get_current_user)])
def list_sales(service: SaleService = Depends(get_sale_service)) -> list[Sale]:
    return service.list_all()


@router.get("/{sale_id}", response_model=SaleRead, dependencies=[Depends(get_current_user)])
def get_sale(sale_id: int, service: SaleService = Depends(get_sale_service)) -> Sale:
    try:
        return service.get(sale_id)
    except SaleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found."
        ) from exc


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale_in: SaleCreate,
    current_user: User = Depends(_can_write),
    service: SaleService = Depends(get_sale_service),
) -> Sale:
    try:
        return service.create(sale_in, sold_by_id=current_user.id)
    except InvalidWarehouseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="warehouse_id does not exist."
        ) from exc
    except InvalidProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Product {exc.product_id} does not exist.",
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Product {exc.product_id}: only {exc.available} available, "
                f"requested {exc.requested}."
            ),
        ) from exc
