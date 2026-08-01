from datetime import date

from app.models.inventory_transfer import InventoryTransfer
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.purchase_order_item import PurchaseOrderItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.repositories.reports_repository import AbstractReportsRepository
from app.schemas.reports import (
    InventoryValuationReport,
    InventoryValuationRow,
    ProductMovementReport,
    ProductMovementRow,
    PurchaseHistoryReport,
    PurchaseHistoryRow,
    SalesHistoryReport,
    SalesHistoryRow,
    SupplierPerformanceReport,
    SupplierPerformanceRow,
)
from app.services.product_service import ProductNotFoundError


def _purchase_receipt_row(item: PurchaseOrderItem, order: PurchaseOrder) -> ProductMovementRow:
    return ProductMovementRow(
        timestamp=order.updated_at,
        type="purchase_receipt",
        product_id=item.product_id,
        product_sku="",
        product_name="",
        warehouse=order.warehouse.name,
        quantity_change=item.quantity_ordered,
        reference=f"PO #{order.id}",
    )


def _sale_row(item: SaleItem, sale: Sale) -> ProductMovementRow:
    return ProductMovementRow(
        timestamp=sale.created_at,
        type="sale",
        product_id=item.product_id,
        product_sku="",
        product_name="",
        warehouse=sale.warehouse.name,
        quantity_change=-item.quantity,
        reference=f"Sale #{sale.id}",
    )


def _transfer_rows(transfer: InventoryTransfer) -> tuple[ProductMovementRow, ProductMovementRow]:
    reference = f"Transfer #{transfer.id}"
    transfer_out = ProductMovementRow(
        timestamp=transfer.created_at,
        type="transfer_out",
        product_id=transfer.product_id,
        product_sku="",
        product_name="",
        warehouse=transfer.from_warehouse.name,
        quantity_change=-transfer.quantity,
        reference=reference,
    )
    transfer_in = ProductMovementRow(
        timestamp=transfer.created_at,
        type="transfer_in",
        product_id=transfer.product_id,
        product_sku="",
        product_name="",
        warehouse=transfer.to_warehouse.name,
        quantity_change=transfer.quantity,
        reference=reference,
    )
    return transfer_out, transfer_in


class ReportsService:
    def __init__(self, repository: AbstractReportsRepository) -> None:
        self._repository = repository

    def get_inventory_valuation(self) -> InventoryValuationReport:
        rows = [
            InventoryValuationRow(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                category=product.category.name,
                supplier=product.supplier.company_name,
                total_quantity=quantity,
                purchase_price=product.purchase_price,
                selling_price=product.selling_price,
                value_at_cost=quantity * product.purchase_price,
                potential_revenue=quantity * product.selling_price,
            )
            for product, quantity in self._repository.get_inventory_valuation()
        ]
        return InventoryValuationReport(
            rows=rows,
            total_value_at_cost=sum(row.value_at_cost for row in rows),
            total_potential_revenue=sum(row.potential_revenue for row in rows),
        )

    def get_sales_history(
        self, start_date: date | None, end_date: date | None
    ) -> SalesHistoryReport:
        rows = []
        for sale in self._repository.get_sales(start_date, end_date):
            item_count = sum(item.quantity for item in sale.items)
            total_revenue = sum(item.quantity * item.unit_price for item in sale.items)
            rows.append(
                SalesHistoryRow(
                    sale_id=sale.id,
                    created_at=sale.created_at,
                    customer_name=sale.customer_name,
                    warehouse=sale.warehouse.name,
                    sold_by=sale.sold_by.full_name,
                    item_count=item_count,
                    total_revenue=total_revenue,
                )
            )
        return SalesHistoryReport(rows=rows, total_revenue=sum(row.total_revenue for row in rows))

    def get_purchase_history(
        self, start_date: date | None, end_date: date | None
    ) -> PurchaseHistoryReport:
        rows = []
        for order in self._repository.get_purchase_orders(start_date, end_date):
            item_count = sum(item.quantity_ordered for item in order.items)
            total_cost = sum(item.quantity_ordered * item.unit_cost for item in order.items)
            rows.append(
                PurchaseHistoryRow(
                    purchase_order_id=order.id,
                    created_at=order.created_at,
                    supplier=order.supplier.company_name,
                    warehouse=order.warehouse.name,
                    status=order.status.value,
                    item_count=item_count,
                    total_cost=total_cost,
                )
            )
        return PurchaseHistoryReport(rows=rows, total_cost=sum(row.total_cost for row in rows))

    def get_product_movement(
        self, product_id: int, start_date: date | None, end_date: date | None
    ) -> ProductMovementReport:
        product = self._repository.get_product(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)

        rows = [
            _purchase_receipt_row(item, order)
            for item, order in self._repository.get_purchase_receipt_events(
                product_id, start_date, end_date
            )
        ]
        rows.extend(
            _sale_row(item, sale)
            for item, sale in self._repository.get_sale_events(product_id, start_date, end_date)
        )
        for transfer in self._repository.get_transfer_events(product_id, start_date, end_date):
            rows.extend(_transfer_rows(transfer))

        for row in rows:
            row.product_sku = product.sku
            row.product_name = product.name

        # Ascending/chronological - a ledger reads start-to-end, unlike the
        # dashboard's "recent activity" feed which sorts descending because
        # it's read newest-first.
        rows.sort(key=lambda row: row.timestamp)
        return ProductMovementReport(rows=rows)

    def get_supplier_performance(self) -> SupplierPerformanceReport:
        orders_by_supplier: dict[int, list[PurchaseOrder]] = {}
        for order in self._repository.get_purchase_orders_with_items():
            orders_by_supplier.setdefault(order.supplier_id, []).append(order)

        rows = []
        for supplier_id, orders in orders_by_supplier.items():
            received = [o for o in orders if o.status == PurchaseOrderStatus.RECEIVED]
            cancelled = [o for o in orders if o.status == PurchaseOrderStatus.CANCELLED]
            total_spend = sum(
                item.unit_cost * item.quantity_ordered for o in received for item in o.items
            )

            average_lead_time_days = (
                sum((o.updated_at - o.created_at).total_seconds() / 86400 for o in received)
                / len(received)
                if received
                else None
            )

            on_time_flags = [
                o.updated_at.date() <= o.expected_delivery_date
                for o in received
                if o.expected_delivery_date is not None
            ]
            on_time_rate = sum(on_time_flags) / len(on_time_flags) if on_time_flags else None

            rows.append(
                SupplierPerformanceRow(
                    supplier_id=supplier_id,
                    company_name=orders[0].supplier.company_name,
                    total_orders=len(orders),
                    total_received=len(received),
                    total_cancelled=len(cancelled),
                    total_spend=total_spend,
                    average_lead_time_days=average_lead_time_days,
                    on_time_rate=on_time_rate,
                )
            )
        rows.sort(key=lambda row: row.company_name)
        return SupplierPerformanceReport(rows=rows)
