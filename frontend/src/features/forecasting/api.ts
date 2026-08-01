import { apiClient } from '../../api/client';
import type { ProductForecast, TrainingSummary } from './types';

export async function trainForecastModel(): Promise<TrainingSummary> {
  const { data } = await apiClient.post<TrainingSummary>('/forecasting/train');
  return data;
}

export async function predictProductDemand(productId: number): Promise<ProductForecast> {
  const { data } = await apiClient.get<ProductForecast>(
    `/forecasting/products/${productId}/predict`,
  );
  return data;
}
