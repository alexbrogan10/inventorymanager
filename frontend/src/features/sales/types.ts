import type { Warehouse } from '../warehouses/types';

// Deliberately not the full Product type - a sale line only needs enough to
// identify and display the product; see SaleItemProductRead on the backend
// for why total_quantity isn't part of this shape.
export interface SaleItemProduct {
  id: number;
  sku: string;
  name: string;
  unit_type: string;
}

export interface SaleItem {
  id: number;
  product: SaleItemProduct;
  quantity: number;
  unit_price: string;
}

export interface Sale {
  id: number;
  warehouse: Warehouse;
  customer_name: string;
  customer_email: string | null;
  customer_phone: string | null;
  notes: string | null;
  sold_by_id: number;
  items: SaleItem[];
  created_at: string;
  updated_at: string;
}

export interface SaleItemInput {
  product_id: number;
  quantity: number;
  unit_price: string;
}

export interface SaleInput {
  warehouse_id: number;
  customer_name: string;
  customer_email: string | null;
  customer_phone: string | null;
  notes: string | null;
  items: SaleItemInput[];
}

export interface PaginatedSales {
  items: Sale[];
  total: number;
  page: number;
  page_size: number;
}

export interface SaleListParams {
  page?: number;
  page_size?: number;
}
