import { apiClient } from './client';

export interface HealthStatus {
  status: string;
}

export async function getReadiness(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>('/health/ready');
  return data;
}
