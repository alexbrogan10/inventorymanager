import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { createSupplier, deleteSupplier, listSuppliers, updateSupplier } from './api';
import type { Supplier, SupplierInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const SUPPLIER: Supplier = {
  id: 1,
  company_name: 'Acme Supply Co.',
  contact_person: 'Jane Doe',
  email: 'jane@acme.example',
  phone: '555-0100',
  address: '123 Warehouse Rd',
  lead_time_days: 7,
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const INPUT: SupplierInput = {
  company_name: 'Acme Supply Co.',
  contact_person: 'Jane Doe',
  email: 'jane@acme.example',
  phone: '555-0100',
  address: '123 Warehouse Rd',
  lead_time_days: 7,
  notes: null,
};

describe('suppliers api', () => {
  it('listSuppliers fetches the supplier list', async () => {
    mockedClient.get.mockResolvedValue({ data: [SUPPLIER] });

    const result = await listSuppliers();

    expect(mockedClient.get).toHaveBeenCalledWith('/suppliers');
    expect(result).toEqual([SUPPLIER]);
  });

  it('createSupplier posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: SUPPLIER });

    const result = await createSupplier(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/suppliers', INPUT);
    expect(result).toEqual(SUPPLIER);
  });

  it('updateSupplier puts to the id path', async () => {
    mockedClient.put.mockResolvedValue({ data: SUPPLIER });

    const result = await updateSupplier(1, INPUT);

    expect(mockedClient.put).toHaveBeenCalledWith('/suppliers/1', INPUT);
    expect(result).toEqual(SUPPLIER);
  });

  it('deleteSupplier deletes the id path', async () => {
    mockedClient.delete.mockResolvedValue({ data: undefined });

    await deleteSupplier(1);

    expect(mockedClient.delete).toHaveBeenCalledWith('/suppliers/1');
  });
});
