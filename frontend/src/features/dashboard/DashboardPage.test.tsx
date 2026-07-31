import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import * as dashboardApi from './api';
import { DashboardPage } from './DashboardPage';
import type { DashboardSummary } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(dashboardApi);

const SUMMARY: DashboardSummary = {
  inventory_value: '1250.50',
  total_products: 12,
  low_stock_count: 2,
  out_of_stock_count: 1,
  pending_purchase_orders_count: 3,
  top_selling_products: [
    { id: 1, sku: 'WIDGET-001', name: 'Widget', total_quantity_sold: 40, total_revenue: '399.60' },
    { id: 2, sku: 'GADGET-002', name: 'Gadget', total_quantity_sold: 25, total_revenue: '375.00' },
  ],
  recent_activity: [
    {
      type: 'sale',
      id: 5,
      timestamp: '2026-01-02T00:00:00Z',
      summary: 'Sale #5 to Jane Customer',
    },
    {
      type: 'purchase_order',
      id: 3,
      timestamp: '2026-01-01T00:00:00Z',
      summary: 'Purchase order #3 from Acme Supply Co. (ordered)',
    },
  ],
};

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider theme={getTheme('light')}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </ThemeProvider>,
  );
}

describe('DashboardPage', () => {
  it('renders the KPI tiles from the dashboard summary', async () => {
    mockedApi.getDashboardSummary.mockResolvedValue(SUMMARY);

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('$1,250.50')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders recent activity items', async () => {
    mockedApi.getDashboardSummary.mockResolvedValue(SUMMARY);

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Sale #5 to Jane Customer')).toBeInTheDocument();
    expect(
      screen.getByText('Purchase order #3 from Acme Supply Co. (ordered)'),
    ).toBeInTheDocument();
  });

  it('shows an empty state when there are no sales yet', async () => {
    mockedApi.getDashboardSummary.mockResolvedValue({
      ...SUMMARY,
      top_selling_products: [],
      recent_activity: [],
    });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('No sales recorded yet.')).toBeInTheDocument();
    expect(screen.getByText('No recent activity.')).toBeInTheDocument();
  });

  it('shows an error message when the summary fails to load', async () => {
    mockedApi.getDashboardSummary.mockRejectedValue(new Error('Network Error'));

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Failed to load dashboard data.')).toBeInTheDocument();
  });
});
