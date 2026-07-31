export interface TopSellingProduct {
  id: number;
  sku: string;
  name: string;
  total_quantity_sold: number;
  total_revenue: string;
}

export interface RecentActivityItem {
  type: 'sale' | 'purchase_order';
  id: number;
  timestamp: string;
  summary: string;
}

export interface DashboardSummary {
  inventory_value: string;
  total_products: number;
  low_stock_count: number;
  out_of_stock_count: number;
  pending_purchase_orders_count: number;
  top_selling_products: TopSellingProduct[];
  recent_activity: RecentActivityItem[];
}
