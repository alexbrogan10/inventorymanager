import { apiClient } from '../../api/client';
import type { Sale, SaleInput } from './types';

export async function listSales(): Promise<Sale[]> {
  const { data } = await apiClient.get<Sale[]>('/sales');
  return data;
}

export async function getSale(id: number): Promise<Sale> {
  const { data } = await apiClient.get<Sale>(`/sales/${id}`);
  return data;
}

export async function createSale(input: SaleInput): Promise<Sale> {
  const { data } = await apiClient.post<Sale>('/sales', input);
  return data;
}
