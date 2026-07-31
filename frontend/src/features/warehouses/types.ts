export interface Warehouse {
  id: number;
  name: string;
  address: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WarehouseInput {
  name: string;
  address: string;
  notes: string | null;
}
