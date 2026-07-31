export interface InventoryValuationRow {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  supplier: string;
  total_quantity: number;
  purchase_price: string;
  selling_price: string;
  value_at_cost: string;
  potential_revenue: string;
}

export interface InventoryValuationReport {
  rows: InventoryValuationRow[];
  total_value_at_cost: string;
  total_potential_revenue: string;
}

export interface SalesHistoryRow {
  sale_id: number;
  created_at: string;
  customer_name: string;
  warehouse: string;
  sold_by: string;
  item_count: number;
  total_revenue: string;
}

export interface SalesHistoryReport {
  rows: SalesHistoryRow[];
  total_revenue: string;
}

export interface PurchaseHistoryRow {
  purchase_order_id: number;
  created_at: string;
  supplier: string;
  warehouse: string;
  status: string;
  item_count: number;
  total_cost: string;
}

export interface PurchaseHistoryReport {
  rows: PurchaseHistoryRow[];
  total_cost: string;
}

export type ProductMovementEventType = 'purchase_receipt' | 'sale' | 'transfer_in' | 'transfer_out';

export interface ProductMovementRow {
  timestamp: string;
  type: ProductMovementEventType;
  product_id: number;
  product_sku: string;
  product_name: string;
  warehouse: string;
  quantity_change: number;
  reference: string;
}

export interface ProductMovementReport {
  rows: ProductMovementRow[];
}

export interface SupplierPerformanceRow {
  supplier_id: number;
  company_name: string;
  total_orders: number;
  total_received: number;
  total_cancelled: number;
  total_spend: string;
  average_lead_time_days: number | null;
  on_time_rate: number | null;
}

export interface SupplierPerformanceReport {
  rows: SupplierPerformanceRow[];
}

export type ReportFormat = 'json' | 'csv' | 'xlsx';

export interface DateRangeParams {
  start_date?: string;
  end_date?: string;
}
