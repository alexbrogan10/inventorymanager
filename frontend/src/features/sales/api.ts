import { apiClient } from '../../api/client';
import type { PaginatedSales, Sale, SaleInput, SaleListParams } from './types';

export async function listSales(params: SaleListParams = {}): Promise<PaginatedSales> {
  const { data } = await apiClient.get<PaginatedSales>('/sales', { params });
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
