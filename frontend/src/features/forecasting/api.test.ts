import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { predictProductDemand, trainForecastModel } from './api';
import type { ProductForecast, TrainingSummary } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const TRAINING_SUMMARY: TrainingSummary = {
  trained_at: '2026-01-01T00:00:00Z',
  training_row_count: 100,
  accuracy: 0.9,
  feature_importance: { day_of_week: 0.5 },
};

const FORECAST: ProductForecast = {
  product_id: 1,
  sku: 'WIDGET-001',
  name: 'Widget',
  current_quantity: 10,
  predicted_daily_demand: 2.5,
  stock_depletion_date: '2026-02-01',
  reorder_quantity: 20,
  confidence_score: 0.8,
  has_sufficient_history: true,
  model_accuracy: 0.9,
  model_trained_at: '2026-01-01T00:00:00Z',
  feature_importance: { day_of_week: 0.5 },
};

describe('forecasting api', () => {
  it('trainForecastModel posts to /forecasting/train', async () => {
    mockedClient.post.mockResolvedValue({ data: TRAINING_SUMMARY });

    const result = await trainForecastModel();

    expect(mockedClient.post).toHaveBeenCalledWith('/forecasting/train');
    expect(result).toEqual(TRAINING_SUMMARY);
  });

  it('predictProductDemand fetches the product-scoped prediction', async () => {
    mockedClient.get.mockResolvedValue({ data: FORECAST });

    const result = await predictProductDemand(1);

    expect(mockedClient.get).toHaveBeenCalledWith('/forecasting/products/1/predict');
    expect(result).toEqual(FORECAST);
  });
});
