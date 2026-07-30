from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


class AbstractCategoryRepository(Protocol):
    def list_all(self) -> list[Category]: ...

    def get_by_id(self, category_id: int) -> Category | None: ...

    def get_by_name(self, name: str) -> Category | None: ...

    def create(self, *, name: str, description: str | None) -> Category: ...

    def update(self, category: Category, *, name: str, description: str | None) -> Category: ...

    def delete(self, category: Category) -> None: ...


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Category]:
        return list(self._db.execute(select(Category).order_by(Category.name)).scalars())

    def get_by_id(self, category_id: int) -> Category | None:
        return self._db.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self._db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()

    def create(self, *, name: str, description: str | None) -> Category:
        category = Category(name=name, description=description)
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return category

    def update(self, category: Category, *, name: str, description: str | None) -> Category:
        category.name = name
        category.description = description
        self._db.commit()
        self._db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self._db.delete(category)
        self._db.commit()
