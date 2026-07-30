import { apiClient } from '../../api/client';
import type { Product, ProductInput } from './types';

export async function listProducts(): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>('/products');
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
