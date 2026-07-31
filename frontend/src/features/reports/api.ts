import { apiClient } from '../../api/client';
import type {
  DateRangeParams,
  InventoryValuationReport,
  ProductMovementReport,
  PurchaseHistoryReport,
  ReportFormat,
  SalesHistoryReport,
  SupplierPerformanceReport,
} from './types';

export async function getInventoryValuation(): Promise<InventoryValuationReport> {
  const { data } = await apiClient.get<InventoryValuationReport>('/reports/inventory-valuation');
  return data;
}

export async function getSalesHistory(params: DateRangeParams = {}): Promise<SalesHistoryReport> {
  const { data } = await apiClient.get<SalesHistoryReport>('/reports/sales-history', { params });
  return data;
}

export async function getPurchaseHistory(
  params: DateRangeParams = {},
): Promise<PurchaseHistoryReport> {
  const { data } = await apiClient.get<PurchaseHistoryReport>('/reports/purchase-history', {
    params,
  });
  return data;
}

export async function getProductMovement(
  productId: number,
  params: DateRangeParams = {},
): Promise<ProductMovementReport> {
  const { data } = await apiClient.get<ProductMovementReport>('/reports/product-movement', {
    params: { product_id: productId, ...params },
  });
  return data;
}

export async function getSupplierPerformance(): Promise<SupplierPerformanceReport> {
  const { data } = await apiClient.get<SupplierPerformanceReport>('/reports/supplier-performance');
  return data;
}

// Saves a csv/xlsx export to disk: the endpoint returns the file's raw
// bytes with a Content-Disposition header, and a blob URL + synthetic <a>
// click is the standard way to trigger a browser download from an
// axios-fetched response without navigating the SPA away from itself.
export async function downloadReport(
  reportPath: string,
  format: Exclude<ReportFormat, 'json'>,
  filename: string,
  params: Record<string, string | number | undefined> = {},
): Promise<void> {
  const response = await apiClient.get<Blob>(`/reports/${reportPath}`, {
    params: { ...params, format },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
