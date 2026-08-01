import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, AxiosHeaders } from 'axios';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import * as forecastingApi from './api';
import { TrainModelCard } from './TrainModelCard';

vi.mock('./api');

const mockedApi = vi.mocked(forecastingApi);

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('TrainModelCard', () => {
  it('trains the model and shows the resulting summary', async () => {
    mockedApi.trainForecastModel.mockResolvedValue({
      trained_at: '2026-01-05T00:00:00Z',
      training_row_count: 100,
      accuracy: 0.912,
      feature_importance: { product_id: 0.3, day_of_week: 0.2, lag_1: 0.5 },
    });
    const user = userEvent.setup();

    renderWithProviders(<TrainModelCard />);
    await user.click(screen.getByRole('button', { name: /train model/i }));

    expect(await screen.findByText('Trained on 100 rows')).toBeInTheDocument();
    expect(screen.getByText('Accuracy (R²): 0.912')).toBeInTheDocument();
  });

  it('shows "not enough data" when accuracy could not be measured', async () => {
    mockedApi.trainForecastModel.mockResolvedValue({
      trained_at: '2026-01-05T00:00:00Z',
      training_row_count: 3,
      accuracy: null,
      feature_importance: {},
    });
    const user = userEvent.setup();

    renderWithProviders(<TrainModelCard />);
    await user.click(screen.getByRole('button', { name: /train model/i }));

    expect(
      await screen.findByText('Accuracy (R²): not enough data to measure'),
    ).toBeInTheDocument();
  });

  it('shows the server error message when training fails', async () => {
    const error = new AxiosError('Request failed', '422', undefined, undefined, {
      status: 422,
      statusText: 'Unprocessable Content',
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
      data: { detail: 'No products have at least 7 days of continuous sales history to train on.' },
    });
    mockedApi.trainForecastModel.mockRejectedValue(error);
    const user = userEvent.setup();

    renderWithProviders(<TrainModelCard />);
    await user.click(screen.getByRole('button', { name: /train model/i }));

    expect(
      await screen.findByText(
        'No products have at least 7 days of continuous sales history to train on.',
      ),
    ).toBeInTheDocument();
  });
});
