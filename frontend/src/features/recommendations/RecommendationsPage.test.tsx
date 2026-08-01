import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import * as recommendationsApi from './api';
import { RecommendationsPage } from './RecommendationsPage';
import type { RecommendationsReport } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(recommendationsApi);

const EMPTY_REPORT: RecommendationsReport = {
  model_trained: true,
  reorder_suggestions: [],
  overstock_warnings: [],
  slow_moving_products: [],
  seasonal_trends: [],
};

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider theme={getTheme('light')}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </ThemeProvider>,
  );
}

describe('RecommendationsPage', () => {
  it('shows empty states for every section when there is nothing to report', async () => {
    mockedApi.getRecommendations.mockResolvedValue(EMPTY_REPORT);

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('No products need reordering right now.')).toBeInTheDocument();
    expect(screen.getByText('No overstock warnings.')).toBeInTheDocument();
    expect(screen.getByText('No slow-moving products.')).toBeInTheDocument();
    expect(screen.getByText('No seasonal trends detected.')).toBeInTheDocument();
    expect(screen.queryByText(/model to be trained first/i)).not.toBeInTheDocument();
  });

  it('shows a hint when the forecasting model has not been trained', async () => {
    mockedApi.getRecommendations.mockResolvedValue({ ...EMPTY_REPORT, model_trained: false });

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText(/model to be trained first/i)).toBeInTheDocument();
  });

  it('renders reorder suggestions', async () => {
    mockedApi.getRecommendations.mockResolvedValue({
      ...EMPTY_REPORT,
      reorder_suggestions: [
        {
          product_id: 1,
          sku: 'WIDGET-001',
          name: 'Widget',
          current_quantity: 5,
          predicted_daily_demand: 4.2,
          stock_depletion_date: '2026-02-01',
          days_until_depletion: 3,
          reorder_quantity: 25,
          confidence_score: 0.83,
        },
      ],
    });

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('WIDGET-001')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('83%')).toBeInTheDocument();
  });

  it('renders overstock warnings with reasons', async () => {
    mockedApi.getRecommendations.mockResolvedValue({
      ...EMPTY_REPORT,
      overstock_warnings: [
        {
          product_id: 2,
          sku: 'GADGET-002',
          name: 'Gadget',
          current_quantity: 100,
          maximum_quantity: 50,
          days_of_supply: null,
          reasons: ['Stock (100) exceeds maximum_quantity (50)'],
        },
      ],
    });

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('GADGET-002')).toBeInTheDocument();
    expect(screen.getByText('Stock (100) exceeds maximum_quantity (50)')).toBeInTheDocument();
  });

  it('renders slow-moving products, including never-sold ones', async () => {
    mockedApi.getRecommendations.mockResolvedValue({
      ...EMPTY_REPORT,
      slow_moving_products: [
        {
          product_id: 3,
          sku: 'STALE-003',
          name: 'Stale Item',
          current_quantity: 20,
          quantity_sold_last_60_days: 0,
          days_since_last_sale: null,
        },
      ],
    });

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('STALE-003')).toBeInTheDocument();
    expect(screen.getByText('Never sold')).toBeInTheDocument();
  });

  it('renders seasonal trends with a readable pattern label', async () => {
    mockedApi.getRecommendations.mockResolvedValue({
      ...EMPTY_REPORT,
      seasonal_trends: [
        {
          product_id: 4,
          sku: 'WEEKEND-004',
          name: 'Weekend Widget',
          pattern: 'weekend_spike',
          weekend_to_weekday_ratio: 3.5,
        },
      ],
    });

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('WEEKEND-004')).toBeInTheDocument();
    expect(screen.getByText('Weekend spike')).toBeInTheDocument();
  });

  it('shows an error message when the request fails', async () => {
    mockedApi.getRecommendations.mockRejectedValue(new Error('Network Error'));

    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('Failed to load recommendations.')).toBeInTheDocument();
  });
});
