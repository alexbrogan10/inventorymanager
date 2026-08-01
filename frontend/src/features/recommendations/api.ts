import { apiClient } from '../../api/client';
import type { RecommendationsReport } from './types';

export async function getRecommendations(): Promise<RecommendationsReport> {
  const { data } = await apiClient.get<RecommendationsReport>('/recommendations');
  return data;
}
