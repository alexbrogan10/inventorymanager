"""Supplier CRUD. Same read/write access split as categories.py - see there
for the reasoning.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.supplier import Supplier
from app.models.user import UserRole
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.supplier_service import (
    DuplicateSupplierNameError,
    SupplierNotFoundError,
    SupplierService,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_supplier_service(db: Session = Depends(get_db)) -> SupplierService:
    return SupplierService(SupplierRepository(db))


@router.get("", response_model=list[SupplierRead], dependencies=[Depends(get_current_user)])
def list_suppliers(service: SupplierService = Depends(get_supplier_service)) -> list[Supplier]:
    return service.list_all()


@router.get("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(get_current_user)])
def get_supplier(
    supplier_id: int, service: SupplierService = Depends(get_supplier_service)
) -> Supplier:
    try:
        return service.get(supplier_id)
    except SupplierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found."
        ) from exc


@router.post(
    "",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_can_write)],
)
def create_supplier(
    supplier_in: SupplierCreate, service: SupplierService = Depends(get_supplier_service)
) -> Supplier:
    try:
        return service.create(supplier_in)
    except DuplicateSupplierNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier with that company name already exists.",
        ) from exc


@router.put("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(_can_write)])
def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    service: SupplierService = Depends(get_supplier_service),
) -> Supplier:
    try:
        return service.update(supplier_id, supplier_in)
    except SupplierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found."
        ) from exc
    except DuplicateSupplierNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier with that company name already exists.",
        ) from exc


@router.delete(
    "/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_can_write)]
)
def delete_supplier(
    supplier_id: int, service: SupplierService = Depends(get_supplier_service)
) -> None:
    try:
        service.delete(supplier_id)
    except SupplierNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found."
        ) from exc
