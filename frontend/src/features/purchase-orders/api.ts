import { apiClient } from '../../api/client';
import type { PurchaseOrder, PurchaseOrderInput } from './types';

export async function listPurchaseOrders(): Promise<PurchaseOrder[]> {
  const { data } = await apiClient.get<PurchaseOrder[]>('/purchase-orders');
  return data;
}

export async function getPurchaseOrder(id: number): Promise<PurchaseOrder> {
  const { data } = await apiClient.get<PurchaseOrder>(`/purchase-orders/${id}`);
  return data;
}

export async function createPurchaseOrder(input: PurchaseOrderInput): Promise<PurchaseOrder> {
  const { data } = await apiClient.post<PurchaseOrder>('/purchase-orders', input);
  return data;
}

export async function shipPurchaseOrder(id: number): Promise<PurchaseOrder> {
  const { data } = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/ship`);
  return data;
}

export async function receivePurchaseOrder(id: number): Promise<PurchaseOrder> {
  const { data } = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/receive`);
  return data;
}

export async function cancelPurchaseOrder(id: number): Promise<PurchaseOrder> {
  const { data } = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/cancel`);
  return data;
}
