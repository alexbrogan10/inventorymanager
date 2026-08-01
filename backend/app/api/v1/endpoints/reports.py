"""Reports & Export: 5 read-only reports, each available as JSON (for the
frontend's own table view) or as a CSV/XLSX file download. Read access is
any authenticated user - these are queries over existing data, not writes.

"format" varies the return type per request (a Pydantic schema for JSON, a
file `Response` for csv/xlsx), so routes deliberately don't declare a single
`response_model=` - the shape isn't fixed at declaration time.

CSV/XLSX satisfy this project's "Power BI export" requirement: Power BI
natively imports both formats, so a file download is a complete answer
without building a live connector integration - see docs/ARCHITECTURE.md.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.export import to_csv_response, to_xlsx_response
from app.repositories.reports_repository import ReportsRepository
from app.services.product_service import ProductNotFoundError
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])

ReportFormat = Literal["json", "csv", "xlsx"]


def get_reports_service(db: Session = Depends(get_db)) -> ReportsService:
    return ReportsService(ReportsRepository(db))


def _export_rows(rows: list[BaseModel]) -> list[dict[str, Any]]:
    """Flatten Pydantic rows for csv/xlsx: Decimals become floats since
    neither the csv writer nor openpyxl's cell writer accept Decimal
    directly, and a report is display data, not a precision-critical
    computation input."""
    converted = []
    for row in rows:
        converted.append(
            {
                key: (float(value) if isinstance(value, Decimal) else value)
                for key, value in row.model_dump().items()
            }
        )
    return converted


def _respond(
    report_rows: list[BaseModel], report: BaseModel, report_format: ReportFormat, filename: str
) -> Any:
    if report_format == "csv":
        return to_csv_response(_export_rows(report_rows), f"{filename}.csv")
    if report_format == "xlsx":
        return to_xlsx_response(_export_rows(report_rows), f"{filename}.xlsx")
    return report


@router.get("/inventory-valuation")
def get_inventory_valuation_report(
    format: ReportFormat = "json",
    service: ReportsService = Depends(get_reports_service),
) -> Any:
    report = service.get_inventory_valuation()
    return _respond(list(report.rows), report, format, "inventory-valuation")


@router.get("/sales-history")
def get_sales_history_report(
    format: ReportFormat = "json",
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> Any:
    report = service.get_sales_history(start_date, end_date)
    return _respond(list(report.rows), report, format, "sales-history")


@router.get("/purchase-history")
def get_purchase_history_report(
    format: ReportFormat = "json",
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> Any:
    report = service.get_purchase_history(start_date, end_date)
    return _respond(list(report.rows), report, format, "purchase-history")


@router.get("/product-movement")
def get_product_movement_report(
    product_id: int,
    format: ReportFormat = "json",
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> Any:
    try:
        report = service.get_product_movement(product_id, start_date, end_date)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found"
        ) from exc
    return _respond(list(report.rows), report, format, "product-movement")


@router.get("/supplier-performance")
def get_supplier_performance_report(
    format: ReportFormat = "json",
    service: ReportsService = Depends(get_reports_service),
) -> Any:
    report = service.get_supplier_performance()
    return _respond(list(report.rows), report, format, "supplier-performance")
