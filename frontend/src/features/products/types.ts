import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';

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
  current_quantity: number;
  minimum_quantity: number;
  maximum_quantity: number | null;
  warehouse_location: string | null;
  unit_type: string;
  image_url: string | null;
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
  current_quantity: number;
  minimum_quantity: number;
  maximum_quantity: number | null;
  warehouse_location: string | null;
  unit_type: string;
}
