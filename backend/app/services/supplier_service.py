from app.models.supplier import Supplier
from app.repositories.supplier_repository import AbstractSupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierNotFoundError(Exception):
    """Raised when a supplier id doesn't exist."""


class DuplicateSupplierNameError(Exception):
    """Raised when a company name is already in use by another supplier."""


class SupplierService:
    def __init__(self, repository: AbstractSupplierRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[Supplier]:
        return self._repository.list_all()

    def get(self, supplier_id: int) -> Supplier:
        supplier = self._repository.get_by_id(supplier_id)
        if supplier is None:
            raise SupplierNotFoundError(supplier_id)
        return supplier

    def create(self, supplier_in: SupplierCreate) -> Supplier:
        if self._repository.get_by_company_name(supplier_in.company_name) is not None:
            raise DuplicateSupplierNameError(supplier_in.company_name)
        return self._repository.create(**supplier_in.model_dump())

    def update(self, supplier_id: int, supplier_in: SupplierUpdate) -> Supplier:
        supplier = self.get(supplier_id)

        existing = self._repository.get_by_company_name(supplier_in.company_name)
        if existing is not None and existing.id != supplier_id:
            raise DuplicateSupplierNameError(supplier_in.company_name)

        return self._repository.update(supplier, **supplier_in.model_dump())

    def delete(self, supplier_id: int) -> None:
        self._repository.delete(self.get(supplier_id))
