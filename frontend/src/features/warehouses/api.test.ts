import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { createWarehouse, deleteWarehouse, listWarehouses, updateWarehouse } from './api';
import type { Warehouse, WarehouseInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const WAREHOUSE: Warehouse = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const INPUT: WarehouseInput = { name: 'Main Warehouse', address: '1 Main St', notes: null };

describe('warehouses api', () => {
  it('listWarehouses fetches the warehouse list', async () => {
    mockedClient.get.mockResolvedValue({ data: [WAREHOUSE] });

    const result = await listWarehouses();

    expect(mockedClient.get).toHaveBeenCalledWith('/warehouses');
    expect(result).toEqual([WAREHOUSE]);
  });

  it('createWarehouse posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: WAREHOUSE });

    const result = await createWarehouse(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/warehouses', INPUT);
    expect(result).toEqual(WAREHOUSE);
  });

  it('updateWarehouse puts to the id path', async () => {
    mockedClient.put.mockResolvedValue({ data: WAREHOUSE });

    const result = await updateWarehouse(1, INPUT);

    expect(mockedClient.put).toHaveBeenCalledWith('/warehouses/1', INPUT);
    expect(result).toEqual(WAREHOUSE);
  });

  it('deleteWarehouse deletes the id path', async () => {
    mockedClient.delete.mockResolvedValue({ data: undefined });

    await deleteWarehouse(1);

    expect(mockedClient.delete).toHaveBeenCalledWith('/warehouses/1');
  });
});
