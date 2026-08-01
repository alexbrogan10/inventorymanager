import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { getRecommendations } from './api';
import type { RecommendationsReport } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const REPORT: RecommendationsReport = {
  model_trained: true,
  reorder_suggestions: [],
  overstock_warnings: [],
  slow_moving_products: [],
  seasonal_trends: [],
};

describe('recommendations api', () => {
  it('getRecommendations fetches the report', async () => {
    mockedClient.get.mockResolvedValue({ data: REPORT });

    const result = await getRecommendations();

    expect(mockedClient.get).toHaveBeenCalledWith('/recommendations');
    expect(result).toEqual(REPORT);
  });
});
