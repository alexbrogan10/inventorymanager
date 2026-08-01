import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { getDashboardSummary } from './api';
import type { DashboardSummary } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const SUMMARY: DashboardSummary = {
  inventory_value: '1000.00',
  total_products: 5,
  low_stock_count: 1,
  out_of_stock_count: 0,
  pending_purchase_orders_count: 2,
  top_selling_products: [],
  recent_activity: [],
};

describe('dashboard api', () => {
  it('getDashboardSummary fetches the summary', async () => {
    mockedClient.get.mockResolvedValue({ data: SUMMARY });

    const result = await getDashboardSummary();

    expect(mockedClient.get).toHaveBeenCalledWith('/dashboard/summary');
    expect(result).toEqual(SUMMARY);
  });
});
