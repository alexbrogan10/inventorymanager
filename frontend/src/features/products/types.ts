import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';
import type { Warehouse } from '../warehouses/types';

export interface Product {
  id: number;
  sku: string;
  barcode: string | null;
  name: string;
  description: string | null;
  category_id: number;
  supplier_id: number;
  category: Category;
  supplier: Supplier;
  // Decimal fields are serialized as strings by the API to preserve exact
  // precision - convert with Number() only where arithmetic/display needs it.
  purchase_price: string;
  selling_price: string;
  minimum_quantity: number;
  maximum_quantity: number | null;
  unit_type: string;
  image_url: string | null;
  // Sum of stock across every warehouse (see InventoryLevel on the backend) -
  // not something you set directly; use setProductInventoryLevel/
  // transferProductInventory instead.
  total_quantity: number;
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  sku: string;
  barcode: string | null;
  name: string;
  description: string | null;
  category_id: number;
  supplier_id: number;
  purchase_price: string;
  selling_price: string;
  minimum_quantity: number;
  maximum_quantity: number | null;
  unit_type: string;
}

export interface InventoryLevel {
  warehouse: Warehouse;
  quantity: number;
}
