import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { AxiosError, AxiosHeaders } from 'axios';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import * as forecastingApi from './api';
import { ForecastPanel } from './ForecastPanel';
import type { ProductForecast } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(forecastingApi);

const FORECAST: ProductForecast = {
  product_id: 1,
  sku: 'WIDGET-001',
  name: 'Widget',
  current_quantity: 50,
  predicted_daily_demand: 4.2,
  stock_depletion_date: '2026-02-01',
  reorder_quantity: 25,
  confidence_score: 0.83,
  has_sufficient_history: true,
  model_accuracy: 0.9,
  model_trained_at: '2026-01-05T00:00:00Z',
  feature_importance: { product_id: 0.3, lag_1: 0.7 },
};

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('ForecastPanel', () => {
  it('renders forecast metrics when the model has sufficient history', async () => {
    mockedApi.predictProductDemand.mockResolvedValue(FORECAST);

    renderWithProviders(<ForecastPanel productId={1} />);

    expect(await screen.findByText('4.2')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('83%')).toBeInTheDocument();
    expect(screen.getByText('Model accuracy (R²): 0.900')).toBeInTheDocument();
  });

  it('shows a fallback notice when the product has insufficient history', async () => {
    mockedApi.predictProductDemand.mockResolvedValue({
      ...FORECAST,
      has_sufficient_history: false,
      predicted_daily_demand: 0,
      stock_depletion_date: null,
      confidence_score: 0,
    });

    renderWithProviders(<ForecastPanel productId={1} />);

    expect(
      await screen.findByText(
        'Not enough sales history yet for a model-based forecast - showing a simple reorder recommendation instead.',
      ),
    ).toBeInTheDocument();
  });

  it('shows a message when the model has not been trained yet', async () => {
    const error = new AxiosError('Request failed', '409', undefined, undefined, {
      status: 409,
      statusText: 'Conflict',
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
      data: { detail: 'The forecasting model has not been trained yet.' },
    });
    mockedApi.predictProductDemand.mockRejectedValue(error);

    renderWithProviders(<ForecastPanel productId={1} />);

    expect(
      await screen.findByText(/the forecasting model hasn.t been trained yet/i),
    ).toBeInTheDocument();
  });
});
