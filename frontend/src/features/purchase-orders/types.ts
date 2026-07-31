import type { Supplier } from '../suppliers/types';
import type { Warehouse } from '../warehouses/types';

export type PurchaseOrderStatus = 'ordered' | 'shipped' | 'received' | 'cancelled';

// Deliberately not the full Product type - a PO line only needs enough to
// identify and display the product; see PurchaseOrderItemProductRead on the
// backend for why total_quantity isn't part of this shape.
export interface PurchaseOrderItemProduct {
  id: number;
  sku: string;
  name: string;
  unit_type: string;
}

export interface PurchaseOrderItem {
  id: number;
  product: PurchaseOrderItemProduct;
  quantity_ordered: number;
  unit_cost: string;
  quantity_received: number;
}

export interface PurchaseOrder {
  id: number;
  supplier: Supplier;
  warehouse: Warehouse;
  status: PurchaseOrderStatus;
  expected_delivery_date: string | null;
  notes: string | null;
  created_by_id: number;
  items: PurchaseOrderItem[];
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderItemInput {
  product_id: number;
  quantity_ordered: number;
  unit_cost: string;
}

export interface PurchaseOrderInput {
  supplier_id: number;
  warehouse_id: number;
  expected_delivery_date: string | null;
  notes: string | null;
  items: PurchaseOrderItemInput[];
}
