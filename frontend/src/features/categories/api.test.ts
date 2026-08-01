import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { createCategory, deleteCategory, listCategories, updateCategory } from './api';
import type { Category, CategoryInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const CATEGORY: Category = {
  id: 1,
  name: 'Electronics',
  description: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const INPUT: CategoryInput = { name: 'Electronics', description: null };

describe('categories api', () => {
  it('listCategories fetches the category list', async () => {
    mockedClient.get.mockResolvedValue({ data: [CATEGORY] });

    const result = await listCategories();

    expect(mockedClient.get).toHaveBeenCalledWith('/categories');
    expect(result).toEqual([CATEGORY]);
  });

  it('createCategory posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: CATEGORY });

    const result = await createCategory(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/categories', INPUT);
    expect(result).toEqual(CATEGORY);
  });

  it('updateCategory puts to the id path', async () => {
    mockedClient.put.mockResolvedValue({ data: CATEGORY });

    const result = await updateCategory(1, INPUT);

    expect(mockedClient.put).toHaveBeenCalledWith('/categories/1', INPUT);
    expect(result).toEqual(CATEGORY);
  });

  it('deleteCategory deletes the id path', async () => {
    mockedClient.delete.mockResolvedValue({ data: undefined });

    await deleteCategory(1);

    expect(mockedClient.delete).toHaveBeenCalledWith('/categories/1');
  });
});
