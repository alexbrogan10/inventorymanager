import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import {
  downloadReport,
  getInventoryValuation,
  getProductMovement,
  getPurchaseHistory,
  getSalesHistory,
  getSupplierPerformance,
} from './api';
import type {
  InventoryValuationReport,
  ProductMovementReport,
  PurchaseHistoryReport,
  SalesHistoryReport,
  SupplierPerformanceReport,
} from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('reports api', () => {
  it('getInventoryValuation fetches the report', async () => {
    const report: InventoryValuationReport = {
      rows: [],
      total_value_at_cost: '0.00',
      total_potential_revenue: '0.00',
    };
    mockedClient.get.mockResolvedValue({ data: report });

    const result = await getInventoryValuation();

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/inventory-valuation');
    expect(result).toEqual(report);
  });

  it('getSalesHistory fetches the report with date-range params', async () => {
    const report: SalesHistoryReport = { rows: [], total_revenue: '0.00' };
    mockedClient.get.mockResolvedValue({ data: report });

    const result = await getSalesHistory({ start_date: '2026-01-01', end_date: '2026-01-31' });

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/sales-history', {
      params: { start_date: '2026-01-01', end_date: '2026-01-31' },
    });
    expect(result).toEqual(report);
  });

  it('getPurchaseHistory fetches the report with date-range params', async () => {
    const report: PurchaseHistoryReport = { rows: [], total_cost: '0.00' };
    mockedClient.get.mockResolvedValue({ data: report });

    const result = await getPurchaseHistory({ start_date: '2026-01-01' });

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/purchase-history', {
      params: { start_date: '2026-01-01' },
    });
    expect(result).toEqual(report);
  });

  it('getProductMovement merges the product id into the params', async () => {
    const report: ProductMovementReport = { rows: [] };
    mockedClient.get.mockResolvedValue({ data: report });

    const result = await getProductMovement(7, { start_date: '2026-01-01' });

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/product-movement', {
      params: { product_id: 7, start_date: '2026-01-01' },
    });
    expect(result).toEqual(report);
  });

  it('getSupplierPerformance fetches the report', async () => {
    const report: SupplierPerformanceReport = { rows: [] };
    mockedClient.get.mockResolvedValue({ data: report });

    const result = await getSupplierPerformance();

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/supplier-performance');
    expect(result).toEqual(report);
  });

  it('downloadReport fetches the blob and triggers a browser download', async () => {
    const blob = new Blob(['sku,name'], { type: 'text/csv' });
    mockedClient.get.mockResolvedValue({ data: blob });
    const createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    await downloadReport('sales-history', 'csv', 'sales.csv', { start_date: '2026-01-01' });

    expect(mockedClient.get).toHaveBeenCalledWith('/reports/sales-history', {
      params: { start_date: '2026-01-01', format: 'csv' },
      responseType: 'blob',
    });
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});
