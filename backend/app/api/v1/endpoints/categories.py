"""Category CRUD. Read access is any authenticated user; write access
(create/update/delete) is restricted to managers and admins - employees can
browse categories but not restructure them.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.category import Category
from app.models.user import UserRole
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category_service import (
    CategoryNotFoundError,
    CategoryService,
    DuplicateCategoryNameError,
)

router = APIRouter(prefix="/categories", tags=["categories"])

_can_write = require_roles(UserRole.ADMIN, UserRole.MANAGER)


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(CategoryRepository(db))


@router.get("", response_model=list[CategoryRead], dependencies=[Depends(get_current_user)])
def list_categories(service: CategoryService = Depends(get_category_service)) -> list[Category]:
    return service.list_all()


@router.get("/{category_id}", response_model=CategoryRead, dependencies=[Depends(get_current_user)])
def get_category(
    category_id: int, service: CategoryService = Depends(get_category_service)
) -> Category:
    try:
        return service.get(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        ) from exc


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_can_write)],
)
def create_category(
    category_in: CategoryCreate, service: CategoryService = Depends(get_category_service)
) -> Category:
    try:
        return service.create(category_in)
    except DuplicateCategoryNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A category with that name already exists."
        ) from exc


@router.put("/{category_id}", response_model=CategoryRead, dependencies=[Depends(_can_write)])
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
) -> Category:
    try:
        return service.update(category_id, category_in)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        ) from exc
    except DuplicateCategoryNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A category with that name already exists."
        ) from exc


@router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_can_write)]
)
def delete_category(
    category_id: int, service: CategoryService = Depends(get_category_service)
) -> None:
    try:
        service.delete(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        ) from exc
