"""Bulk product import from CSV.

Each row is turned into a `ProductCreate` and handed to
`ProductService.create` - the same validation and duplicate/reference
checks a single product creation goes through in the UI apply here too,
so there's exactly one place that decides what a valid product is. This
module's own job is narrower: parsing CSV text into rows, resolving
category/supplier names to ids, coercing strings to the right types, and
turning whatever goes wrong into a per-row error message instead of an
exception that would abort the whole file.

Rows are imported one at a time, each committed immediately by
`ProductService.create` - so a file with 100 good rows and 1 bad row
still leaves 100 products created, and the bad row is reported for the
user to fix and re-upload alone rather than resubmitting everything.
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from app.repositories.category_repository import AbstractCategoryRepository
from app.repositories.supplier_repository import AbstractSupplierRepository
from app.schemas.product import ProductCreate
from app.schemas.product_import import ProductImportReport, ProductImportRowError
from app.services.product_service import (
    DuplicateBarcodeError,
    DuplicateSkuError,
    InvalidCategoryError,
    InvalidSupplierError,
    ProductService,
)

REQUIRED_COLUMNS = (
    "sku",
    "name",
    "category_name",
    "supplier_name",
    "purchase_price",
    "selling_price",
)


class MissingColumnsError(Exception):
    """Raised when the CSV header is missing one or more required columns."""

    def __init__(self, columns: list[str]) -> None:
        self.columns = columns
        super().__init__(f"Missing required column(s): {', '.join(columns)}")


class _RowResult(NamedTuple):
    sku: str | None
    messages: list[str]


class ProductImportService:
    def __init__(
        self,
        product_service: ProductService,
        categories: AbstractCategoryRepository,
        suppliers: AbstractSupplierRepository,
    ) -> None:
        self._product_service = product_service
        self._categories = categories
        self._suppliers = suppliers

    def import_csv(self, content: str) -> ProductImportReport:
        reader = csv.DictReader(io.StringIO(content))
        header = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing_columns:
            raise MissingColumnsError(missing_columns)

        row_errors: list[ProductImportRowError] = []
        imported_skus: list[str] = []
        total_rows = 0

        # `line_number` starts at 2: line 1 is the header, so this always
        # matches the line a user would see if they opened the file directly.
        for line_number, row in enumerate(reader, start=2):
            total_rows += 1
            result = self._import_row(row)
            if result.messages:
                row_errors.append(ProductImportRowError(row=line_number, messages=result.messages))
            else:
                assert result.sku is not None
                imported_skus.append(result.sku)

        return ProductImportReport(
            total_rows=total_rows,
            imported_count=len(imported_skus),
            failed_count=len(row_errors),
            imported_skus=imported_skus,
            row_errors=row_errors,
        )

    def _import_row(self, row: dict[str, str | None]) -> _RowResult:
        messages: list[str] = []

        def required(column: str) -> str:
            value = (row.get(column) or "").strip()
            if not value:
                messages.append(f"Missing required value for '{column}'")
            return value

        sku = required("sku")
        name = required("name")
        category_name = required("category_name")
        supplier_name = required("supplier_name")
        purchase_price_raw = required("purchase_price")
        selling_price_raw = required("selling_price")

        barcode = (row.get("barcode") or "").strip() or None
        description = (row.get("description") or "").strip() or None
        unit_type = (row.get("unit_type") or "").strip() or "each"

        category = self._categories.get_by_name(category_name) if category_name else None
        if category_name and category is None:
            messages.append(f"Unknown category '{category_name}'")

        supplier = self._suppliers.get_by_company_name(supplier_name) if supplier_name else None
        if supplier_name and supplier is None:
            messages.append(f"Unknown supplier '{supplier_name}'")

        purchase_price = self._parse_decimal(purchase_price_raw, "purchase_price", messages)
        selling_price = self._parse_decimal(selling_price_raw, "selling_price", messages)
        minimum_quantity = self._parse_int(
            row.get("minimum_quantity"), "minimum_quantity", messages, default=0
        )
        maximum_quantity = self._parse_optional_int(
            row.get("maximum_quantity"), "maximum_quantity", messages
        )

        if messages:
            return _RowResult(sku=None, messages=messages)

        assert category is not None
        assert supplier is not None
        assert purchase_price is not None
        assert selling_price is not None

        try:
            product_in = ProductCreate(
                sku=sku,
                barcode=barcode,
                name=name,
                description=description,
                category_id=category.id,
                supplier_id=supplier.id,
                purchase_price=purchase_price,
                selling_price=selling_price,
                minimum_quantity=minimum_quantity,
                maximum_quantity=maximum_quantity,
                unit_type=unit_type,
            )
        except ValidationError as exc:
            messages = [self._format_validation_error(e) for e in exc.errors()]
            return _RowResult(sku=None, messages=messages)

        try:
            product = self._product_service.create(product_in)
        except DuplicateSkuError:
            return _RowResult(sku=None, messages=[f"SKU '{sku}' already exists"])
        except DuplicateBarcodeError:
            return _RowResult(sku=None, messages=[f"Barcode '{barcode}' already exists"])
        except InvalidCategoryError:
            return _RowResult(sku=None, messages=[f"Unknown category '{category_name}'"])
        except InvalidSupplierError:
            return _RowResult(sku=None, messages=[f"Unknown supplier '{supplier_name}'"])

        return _RowResult(sku=product.sku, messages=[])

    @staticmethod
    def _parse_decimal(raw: str, field: str, messages: list[str]) -> Decimal | None:
        if not raw:
            return None
        try:
            return Decimal(raw)
        except InvalidOperation:
            messages.append(f"Invalid number '{raw}' for '{field}'")
            return None

    @staticmethod
    def _parse_int(raw: str | None, field: str, messages: list[str], *, default: int) -> int:
        value = (raw or "").strip()
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            messages.append(f"Invalid integer '{value}' for '{field}'")
            return default

    @staticmethod
    def _parse_optional_int(raw: str | None, field: str, messages: list[str]) -> int | None:
        value = (raw or "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            messages.append(f"Invalid integer '{value}' for '{field}'")
            return None

    @staticmethod
    def _format_validation_error(error: ErrorDetails) -> str:
        field = ".".join(str(part) for part in error["loc"])
        return f"{field}: {error['msg']}"
