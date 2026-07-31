import { apiClient } from '../../api/client';
import type {
  InventoryLevel,
  PaginatedProducts,
  Product,
  ProductInput,
  ProductSearchParams,
} from './types';

export async function listProducts(params: ProductSearchParams = {}): Promise<PaginatedProducts> {
  const { data } = await apiClient.get<PaginatedProducts>('/products', { params });
  return data;
}

export async function getProduct(id: number): Promise<Product> {
  const { data } = await apiClient.get<Product>(`/products/${id}`);
  return data;
}

export async function createProduct(input: ProductInput): Promise<Product> {
  const { data } = await apiClient.post<Product>('/products', input);
  return data;
}

export async function updateProduct(id: number, input: ProductInput): Promise<Product> {
  const { data } = await apiClient.put<Product>(`/products/${id}`, input);
  return data;
}

export async function deleteProduct(id: number): Promise<void> {
  await apiClient.delete(`/products/${id}`);
}

export async function uploadProductImage(id: number, file: File): Promise<Product> {
  const formData = new FormData();
  formData.append('file', file);
  // No explicit Content-Type here - the browser sets multipart/form-data
  // with the correct boundary itself; overriding it manually breaks the upload.
  const { data } = await apiClient.post<Product>(`/products/${id}/image`, formData);
  return data;
}

export async function getProductInventory(productId: number): Promise<InventoryLevel[]> {
  const { data } = await apiClient.get<InventoryLevel[]>(`/products/${productId}/inventory`);
  return data;
}

export async function setProductInventoryLevel(
  productId: number,
  warehouseId: number,
  quantity: number,
): Promise<InventoryLevel[]> {
  const { data } = await apiClient.put<InventoryLevel[]>(
    `/products/${productId}/inventory/${warehouseId}`,
    { quantity },
  );
  return data;
}

export interface TransferInput {
  from_warehouse_id: number;
  to_warehouse_id: number;
  quantity: number;
}

export async function transferProductInventory(
  productId: number,
  input: TransferInput,
): Promise<InventoryLevel[]> {
  const { data } = await apiClient.post<InventoryLevel[]>(`/products/${productId}/transfer`, input);
  return data;
}
