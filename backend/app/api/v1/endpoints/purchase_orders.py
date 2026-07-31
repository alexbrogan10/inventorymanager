"""Purchase orders: read = any authenticated user, create/ship/receive/cancel
= manager/admin, same split as every other business-resource router. There is
no DELETE - a purchase order is a business record, and `cancel` is the
terminal state for one that should no longer be acted on (see
PurchaseOrderService for the full status lifecycle).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.purchase_order import PurchaseOrder
from app.models.user import User, UserRole
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderRead
from app.services.purchase_order_service import (
    InvalidProductError,
    InvalidStatusTransitionError,
    InvalidSupplierError,
    InvalidWarehouseError,
    PurchaseOrderNotFoundError,
    PurchaseOrderService,
)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_purchase_order_service(db: Session = Depends(get_db)) -> PurchaseOrderService:
    return PurchaseOrderService(
        PurchaseOrderRepository(db),
        SupplierRepository(db),
        WarehouseRepository(db),
        ProductRepository(db),
        InventoryRepository(db),
    )


@router.get("", response_model=list[PurchaseOrderRead], dependencies=[Depends(get_current_user)])
def list_purchase_orders(
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> list[PurchaseOrder]:
    return service.list_all()


@router.get(
    "/{purchase_order_id}",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(get_current_user)],
)
def get_purchase_order(
    purchase_order_id: int, service: PurchaseOrderService = Depends(get_purchase_order_service)
) -> PurchaseOrder:
    try:
        return service.get(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found."
        ) from exc


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    order_in: PurchaseOrderCreate,
    current_user: User = Depends(_can_write),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrder:
    try:
        return service.create(order_in, created_by_id=current_user.id)
    except InvalidSupplierError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="supplier_id does not exist."
        ) from exc
    except InvalidWarehouseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="warehouse_id does not exist."
        ) from exc
    except InvalidProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Product {exc.product_id} does not exist.",
        ) from exc


@router.post(
    "/{purchase_order_id}/ship",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(_can_write)],
)
def ship_purchase_order(
    purchase_order_id: int, service: PurchaseOrderService = Depends(get_purchase_order_service)
) -> PurchaseOrder:
    try:
        return service.ship(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found."
        ) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{purchase_order_id}/receive",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(_can_write)],
)
def receive_purchase_order(
    purchase_order_id: int, service: PurchaseOrderService = Depends(get_purchase_order_service)
) -> PurchaseOrder:
    try:
        return service.receive(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found."
        ) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{purchase_order_id}/cancel",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(_can_write)],
)
def cancel_purchase_order(
    purchase_order_id: int, service: PurchaseOrderService = Depends(get_purchase_order_service)
) -> PurchaseOrder:
    try:
        return service.cancel(purchase_order_id)
    except PurchaseOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found."
        ) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
