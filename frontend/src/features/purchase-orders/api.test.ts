import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import {
  cancelPurchaseOrder,
  createPurchaseOrder,
  getPurchaseOrder,
  listPurchaseOrders,
  receivePurchaseOrder,
  shipPurchaseOrder,
} from './api';
import type { PaginatedPurchaseOrders, PurchaseOrder, PurchaseOrderInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const SUPPLIER = {
  id: 1,
  company_name: 'Acme Supply Co.',
  contact_person: 'Jane Doe',
  email: 'jane@acme.example',
  phone: '555-0100',
  address: '123 Warehouse Rd',
  lead_time_days: 7,
  notes: null,
  created_at: '',
  updated_at: '',
};

const WAREHOUSE = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: null,
  created_at: '',
  updated_at: '',
};

const ORDER: PurchaseOrder = {
  id: 1,
  supplier: SUPPLIER,
  warehouse: WAREHOUSE,
  status: 'ordered',
  expected_delivery_date: null,
  notes: null,
  created_by_id: 1,
  items: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const PAGE: PaginatedPurchaseOrders = { items: [ORDER], total: 1, page: 1, page_size: 20 };

const INPUT: PurchaseOrderInput = {
  supplier_id: 1,
  warehouse_id: 1,
  expected_delivery_date: null,
  notes: null,
  items: [{ product_id: 1, quantity_ordered: 10, unit_cost: '4.25' }],
};

describe('purchase orders api', () => {
  it('listPurchaseOrders fetches a paginated page with the given params', async () => {
    mockedClient.get.mockResolvedValue({ data: PAGE });

    const result = await listPurchaseOrders({ page: 2, page_size: 10 });

    expect(mockedClient.get).toHaveBeenCalledWith('/purchase-orders', {
      params: { page: 2, page_size: 10 },
    });
    expect(result).toEqual(PAGE);
  });

  it('getPurchaseOrder fetches a single order by id', async () => {
    mockedClient.get.mockResolvedValue({ data: ORDER });

    const result = await getPurchaseOrder(1);

    expect(mockedClient.get).toHaveBeenCalledWith('/purchase-orders/1');
    expect(result).toEqual(ORDER);
  });

  it('createPurchaseOrder posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: ORDER });

    const result = await createPurchaseOrder(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/purchase-orders', INPUT);
    expect(result).toEqual(ORDER);
  });

  it('shipPurchaseOrder posts to the ship action', async () => {
    mockedClient.post.mockResolvedValue({ data: { ...ORDER, status: 'shipped' } });

    const result = await shipPurchaseOrder(1);

    expect(mockedClient.post).toHaveBeenCalledWith('/purchase-orders/1/ship');
    expect(result.status).toBe('shipped');
  });

  it('receivePurchaseOrder posts to the receive action', async () => {
    mockedClient.post.mockResolvedValue({ data: { ...ORDER, status: 'received' } });

    const result = await receivePurchaseOrder(1);

    expect(mockedClient.post).toHaveBeenCalledWith('/purchase-orders/1/receive');
    expect(result.status).toBe('received');
  });

  it('cancelPurchaseOrder posts to the cancel action', async () => {
    mockedClient.post.mockResolvedValue({ data: { ...ORDER, status: 'cancelled' } });

    const result = await cancelPurchaseOrder(1);

    expect(mockedClient.post).toHaveBeenCalledWith('/purchase-orders/1/cancel');
    expect(result.status).toBe('cancelled');
  });
});
