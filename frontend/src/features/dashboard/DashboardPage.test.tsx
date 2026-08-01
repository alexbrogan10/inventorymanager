import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as forecastingApi from '../forecasting/api';
import * as dashboardApi from './api';
import { DashboardPage } from './DashboardPage';
import type { DashboardSummary } from './types';

vi.mock('./api');
vi.mock('../auth/useAuth');
vi.mock('../forecasting/api');

const mockedApi = vi.mocked(dashboardApi);
const mockedUseAuth = vi.mocked(useAuth);
const mockedForecastingApi = vi.mocked(forecastingApi);

const EMPLOYEE: User = {
  id: 1,
  email: 'employee@example.com',
  full_name: 'Employee User',
  role: 'employee',
  is_active: true,
  created_at: '',
};
const MANAGER: User = { ...EMPLOYEE, id: 2, email: 'manager@example.com', role: 'manager' };

function mockAuth(user: User) {
  mockedUseAuth.mockReturnValue({
    user,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

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
  beforeEach(() => {
    mockAuth(EMPLOYEE);
  });

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

  it('hides the training card from an employee', async () => {
    mockedApi.getDashboardSummary.mockResolvedValue(SUMMARY);

    renderWithProviders(<DashboardPage />);

    await screen.findByText('$1,250.50');
    expect(screen.queryByText('Demand Forecasting Model')).not.toBeInTheDocument();
  });

  it('lets a manager train the forecasting model and shows the summary', async () => {
    mockAuth(MANAGER);
    mockedApi.getDashboardSummary.mockResolvedValue(SUMMARY);
    mockedForecastingApi.trainForecastModel.mockResolvedValue({
      trained_at: '2026-01-05T00:00:00Z',
      training_row_count: 42,
      accuracy: 0.87,
      feature_importance: { product_id: 0.4, lag_1: 0.6 },
    });
    const user = userEvent.setup();

    renderWithProviders(<DashboardPage />);
    await screen.findByText('$1,250.50');
    await user.click(screen.getByRole('button', { name: /train model/i }));

    expect(await screen.findByText('Trained on 42 rows')).toBeInTheDocument();
    expect(screen.getByText('Accuracy (R²): 0.870')).toBeInTheDocument();
  });
});
