"""Warehouse CRUD. Same read/write access split as categories.py and
suppliers.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.user import UserRole
from app.models.warehouse import Warehouse
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services.warehouse_service import (
    DuplicateWarehouseNameError,
    WarehouseNotFoundError,
    WarehouseService,
)

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_warehouse_service(db: Session = Depends(get_db)) -> WarehouseService:
    return WarehouseService(WarehouseRepository(db))


@router.get("", response_model=list[WarehouseRead], dependencies=[Depends(get_current_user)])
def list_warehouses(service: WarehouseService = Depends(get_warehouse_service)) -> list[Warehouse]:
    return service.list_all()


@router.get(
    "/{warehouse_id}", response_model=WarehouseRead, dependencies=[Depends(get_current_user)]
)
def get_warehouse(
    warehouse_id: int, service: WarehouseService = Depends(get_warehouse_service)
) -> Warehouse:
    try:
        return service.get(warehouse_id)
    except WarehouseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found."
        ) from exc


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_can_write)],
)
def create_warehouse(
    warehouse_in: WarehouseCreate, service: WarehouseService = Depends(get_warehouse_service)
) -> Warehouse:
    try:
        return service.create(warehouse_in)
    except DuplicateWarehouseNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with that name already exists.",
        ) from exc


@router.put("/{warehouse_id}", response_model=WarehouseRead, dependencies=[Depends(_can_write)])
def update_warehouse(
    warehouse_id: int,
    warehouse_in: WarehouseUpdate,
    service: WarehouseService = Depends(get_warehouse_service),
) -> Warehouse:
    try:
        return service.update(warehouse_id, warehouse_in)
    except WarehouseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found."
        ) from exc
    except DuplicateWarehouseNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with that name already exists.",
        ) from exc


@router.delete(
    "/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_can_write)]
)
def delete_warehouse(
    warehouse_id: int, service: WarehouseService = Depends(get_warehouse_service)
) -> None:
    try:
        service.delete(warehouse_id)
    except WarehouseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found."
        ) from exc
