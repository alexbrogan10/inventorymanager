import { apiClient } from '../../api/client';
import type { Warehouse, WarehouseInput } from './types';

export async function listWarehouses(): Promise<Warehouse[]> {
  const { data } = await apiClient.get<Warehouse[]>('/warehouses');
  return data;
}

export async function createWarehouse(input: WarehouseInput): Promise<Warehouse> {
  const { data } = await apiClient.post<Warehouse>('/warehouses', input);
  return data;
}

export async function updateWarehouse(id: number, input: WarehouseInput): Promise<Warehouse> {
  const { data } = await apiClient.put<Warehouse>(`/warehouses/${id}`, input);
  return data;
}

export async function deleteWarehouse(id: number): Promise<void> {
  await apiClient.delete(`/warehouses/${id}`);
}
