from app.models.category import Category
from app.repositories.category_repository import AbstractCategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryNotFoundError(Exception):
    """Raised when a category id doesn't exist."""


class DuplicateCategoryNameError(Exception):
    """Raised when a category name is already in use by another category."""


class CategoryService:
    def __init__(self, repository: AbstractCategoryRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[Category]:
        return self._repository.list_all()

    def get(self, category_id: int) -> Category:
        category = self._repository.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError(category_id)
        return category

    def create(self, category_in: CategoryCreate) -> Category:
        if self._repository.get_by_name(category_in.name) is not None:
            raise DuplicateCategoryNameError(category_in.name)
        return self._repository.create(**category_in.model_dump())

    def update(self, category_id: int, category_in: CategoryUpdate) -> Category:
        category = self.get(category_id)

        existing = self._repository.get_by_name(category_in.name)
        if existing is not None and existing.id != category_id:
            raise DuplicateCategoryNameError(category_in.name)

        return self._repository.update(category, **category_in.model_dump())

    def delete(self, category_id: int) -> None:
        self._repository.delete(self.get(category_id))
