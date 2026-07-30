from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier


class AbstractSupplierRepository(Protocol):
    def list_all(self) -> list[Supplier]: ...

    def get_by_id(self, supplier_id: int) -> Supplier | None: ...

    def get_by_company_name(self, company_name: str) -> Supplier | None: ...

    def create(
        self,
        *,
        company_name: str,
        contact_person: str,
        email: str,
        phone: str,
        address: str,
        lead_time_days: int,
        notes: str | None,
    ) -> Supplier: ...

    def update(
        self,
        supplier: Supplier,
        *,
        company_name: str,
        contact_person: str,
        email: str,
        phone: str,
        address: str,
        lead_time_days: int,
        notes: str | None,
    ) -> Supplier: ...

    def delete(self, supplier: Supplier) -> None: ...


class SupplierRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Supplier]:
        return list(self._db.execute(select(Supplier).order_by(Supplier.company_name)).scalars())

    def get_by_id(self, supplier_id: int) -> Supplier | None:
        return self._db.get(Supplier, supplier_id)

    def get_by_company_name(self, company_name: str) -> Supplier | None:
        return self._db.execute(
            select(Supplier).where(Supplier.company_name == company_name)
        ).scalar_one_or_none()

    def create(
        self,
        *,
        company_name: str,
        contact_person: str,
        email: str,
        phone: str,
        address: str,
        lead_time_days: int,
        notes: str | None,
    ) -> Supplier:
        supplier = Supplier(
            company_name=company_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            lead_time_days=lead_time_days,
            notes=notes,
        )
        self._db.add(supplier)
        self._db.commit()
        self._db.refresh(supplier)
        return supplier

    def update(
        self,
        supplier: Supplier,
        *,
        company_name: str,
        contact_person: str,
        email: str,
        phone: str,
        address: str,
        lead_time_days: int,
        notes: str | None,
    ) -> Supplier:
        supplier.company_name = company_name
        supplier.contact_person = contact_person
        supplier.email = email
        supplier.phone = phone
        supplier.address = address
        supplier.lead_time_days = lead_time_days
        supplier.notes = notes
        self._db.commit()
        self._db.refresh(supplier)
        return supplier

    def delete(self, supplier: Supplier) -> None:
        self._db.delete(supplier)
        self._db.commit()
