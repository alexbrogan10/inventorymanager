import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { createSale, getSale, listSales } from './api';
import type { PaginatedSales, Sale, SaleInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const SALE: Sale = {
  id: 1,
  warehouse: {
    id: 1,
    name: 'Main Warehouse',
    address: '1 Main St',
    notes: null,
    created_at: '',
    updated_at: '',
  },
  customer_name: 'Jane Customer',
  customer_email: null,
  customer_phone: null,
  notes: null,
  sold_by_id: 1,
  items: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const PAGE: PaginatedSales = { items: [SALE], total: 1, page: 1, page_size: 20 };

const INPUT: SaleInput = {
  warehouse_id: 1,
  customer_name: 'Jane Customer',
  customer_email: null,
  customer_phone: null,
  notes: null,
  items: [{ product_id: 1, quantity: 2, unit_price: '9.99' }],
};

describe('sales api', () => {
  it('listSales fetches a paginated page with the given params', async () => {
    mockedClient.get.mockResolvedValue({ data: PAGE });

    const result = await listSales({ page: 2, page_size: 10 });

    expect(mockedClient.get).toHaveBeenCalledWith('/sales', {
      params: { page: 2, page_size: 10 },
    });
    expect(result).toEqual(PAGE);
  });

  it('listSales defaults to no params', async () => {
    mockedClient.get.mockResolvedValue({ data: PAGE });

    await listSales();

    expect(mockedClient.get).toHaveBeenCalledWith('/sales', { params: {} });
  });

  it('getSale fetches a single sale by id', async () => {
    mockedClient.get.mockResolvedValue({ data: SALE });

    const result = await getSale(1);

    expect(mockedClient.get).toHaveBeenCalledWith('/sales/1');
    expect(result).toEqual(SALE);
  });

  it('createSale posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: SALE });

    const result = await createSale(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/sales', INPUT);
    expect(result).toEqual(SALE);
  });
});
