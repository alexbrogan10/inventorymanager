import { apiClient } from '../../api/client';
import type { Supplier, SupplierInput } from './types';

export async function listSuppliers(): Promise<Supplier[]> {
  const { data } = await apiClient.get<Supplier[]>('/suppliers');
  return data;
}

export async function createSupplier(input: SupplierInput): Promise<Supplier> {
  const { data } = await apiClient.post<Supplier>('/suppliers', input);
  return data;
}

export async function updateSupplier(id: number, input: SupplierInput): Promise<Supplier> {
  const { data } = await apiClient.put<Supplier>(`/suppliers/${id}`, input);
  return data;
}

export async function deleteSupplier(id: number): Promise<void> {
  await apiClient.delete(`/suppliers/${id}`);
}
