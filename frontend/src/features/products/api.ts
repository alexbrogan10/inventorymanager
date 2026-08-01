import { apiClient } from '../../api/client';
import type {
  InventoryLevel,
  PaginatedProducts,
  Product,
  ProductImportReport,
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

export async function importProducts(file: File): Promise<ProductImportReport> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<ProductImportReport>('/products/import', formData);
  return data;
}

// Saves the CSV template to disk the same way report exports do (blob URL +
// synthetic <a> click) - see features/reports/api.ts's downloadReport.
export async function downloadImportTemplate(): Promise<void> {
  const response = await apiClient.get<Blob>('/products/import/template', {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'product-import-template.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
