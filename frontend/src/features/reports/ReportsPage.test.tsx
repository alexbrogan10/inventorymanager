import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import * as productsApi from '../products/api';
import type { PaginatedProducts } from '../products/types';
import * as reportsApi from './api';
import { ReportsPage } from './ReportsPage';
import type {
  InventoryValuationReport,
  ProductMovementReport,
  PurchaseHistoryReport,
  SalesHistoryReport,
  SupplierPerformanceReport,
} from './types';

vi.mock('./api');
vi.mock('../products/api');

const mockedReportsApi = vi.mocked(reportsApi);
const mockedProductsApi = vi.mocked(productsApi);

const PRODUCTS: PaginatedProducts = {
  items: [
    {
      id: 1,
      sku: 'WIDGET-001',
      barcode: null,
      name: 'Widget',
      description: null,
      category_id: 1,
      supplier_id: 1,
      category: {
        id: 1,
        name: 'Electronics',
        description: null,
        created_at: '',
        updated_at: '',
      },
      supplier: {
        id: 1,
        company_name: 'Acme Supply Co.',
        contact_person: 'Jane Doe',
        email: 'jane@acme.example',
        phone: '555-0100',
        address: '123 Warehouse Rd',
        lead_time_days: 7,
        notes: null,
        created_at: '',
        updated_at: '',
      },
      purchase_price: '5.00',
      selling_price: '9.99',
      minimum_quantity: 10,
      maximum_quantity: null,
      unit_type: 'each',
      image_url: null,
      total_quantity: 20,
      created_at: '',
      updated_at: '',
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
};

const INVENTORY_VALUATION: InventoryValuationReport = {
  rows: [
    {
      product_id: 1,
      sku: 'WIDGET-001',
      name: 'Widget',
      category: 'Electronics',
      supplier: 'Acme Supply Co.',
      total_quantity: 20,
      purchase_price: '5.00',
      selling_price: '9.99',
      value_at_cost: '100.00',
      potential_revenue: '199.80',
    },
  ],
  total_value_at_cost: '100.00',
  total_potential_revenue: '199.80',
};

const SALES_HISTORY: SalesHistoryReport = {
  rows: [
    {
      sale_id: 7,
      created_at: '2026-01-05T00:00:00Z',
      customer_name: 'Jane Customer',
      warehouse: 'Main Warehouse',
      sold_by: 'Test User',
      item_count: 2,
      total_revenue: '19.98',
    },
  ],
  total_revenue: '19.98',
};

const PURCHASE_HISTORY: PurchaseHistoryReport = {
  rows: [
    {
      purchase_order_id: 3,
      created_at: '2026-01-04T00:00:00Z',
      supplier: 'Acme Supply Co.',
      warehouse: 'Main Warehouse',
      status: 'received',
      item_count: 5,
      total_cost: '10.00',
    },
  ],
  total_cost: '10.00',
};

const PRODUCT_MOVEMENT: ProductMovementReport = {
  rows: [
    {
      timestamp: '2026-01-01T00:00:00Z',
      type: 'purchase_receipt',
      product_id: 1,
      product_sku: 'WIDGET-001',
      product_name: 'Widget',
      warehouse: 'Main Warehouse',
      quantity_change: 50,
      reference: 'PO #1',
    },
  ],
};

const SUPPLIER_PERFORMANCE: SupplierPerformanceReport = {
  rows: [
    {
      supplier_id: 1,
      company_name: 'Acme Supply Co.',
      total_orders: 3,
      total_received: 2,
      total_cancelled: 1,
      total_spend: '35.00',
      average_lead_time_days: 0,
      on_time_rate: 0.5,
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

describe('ReportsPage', () => {
  beforeEach(() => {
    mockedProductsApi.listProducts.mockResolvedValue(PRODUCTS);
    mockedReportsApi.getInventoryValuation.mockResolvedValue(INVENTORY_VALUATION);
    mockedReportsApi.getSalesHistory.mockResolvedValue(SALES_HISTORY);
    mockedReportsApi.getPurchaseHistory.mockResolvedValue(PURCHASE_HISTORY);
    mockedReportsApi.getProductMovement.mockResolvedValue(PRODUCT_MOVEMENT);
    mockedReportsApi.getSupplierPerformance.mockResolvedValue(SUPPLIER_PERFORMANCE);
    mockedReportsApi.downloadReport.mockResolvedValue(undefined);
  });

  it('shows the inventory valuation report by default', async () => {
    renderWithProviders(<ReportsPage />);

    expect(await screen.findByText('WIDGET-001')).toBeInTheDocument();
    expect(screen.getAllByText('$100.00').length).toBeGreaterThan(0);
    expect(screen.getAllByText('$199.80').length).toBeGreaterThan(0);
  });

  it('switches to the sales history report and loads its data', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('tab', { name: 'Sales History' }));

    expect(await screen.findByText('Jane Customer')).toBeInTheDocument();
    expect(mockedReportsApi.getSalesHistory).toHaveBeenCalledWith({
      start_date: undefined,
      end_date: undefined,
    });
  });

  it('switches to the purchase history report and loads its data', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('tab', { name: 'Purchase History' }));

    expect(await screen.findByText('Acme Supply Co.')).toBeInTheDocument();
    expect(screen.getAllByText('$10.00').length).toBeGreaterThan(0);
  });

  it('only fetches product movement once a product is selected', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('tab', { name: 'Product Movement' }));

    expect(
      screen.getByText('Select a product above to view its movement history.'),
    ).toBeInTheDocument();
    expect(mockedReportsApi.getProductMovement).not.toHaveBeenCalled();

    await user.click(screen.getByLabelText('Product'));
    await user.click(await screen.findByRole('option', { name: 'WIDGET-001 - Widget' }));

    expect(await screen.findByText('PO #1')).toBeInTheDocument();
    expect(mockedReportsApi.getProductMovement).toHaveBeenCalledWith(1, {
      start_date: undefined,
      end_date: undefined,
    });
  });

  it('shows the supplier performance report with on-time rate as a percentage', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('tab', { name: 'Supplier Performance' }));

    expect(await screen.findByText('50%')).toBeInTheDocument();
  });

  it('downloads a csv export for the active report', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('button', { name: /download csv/i }));

    await waitFor(() =>
      expect(mockedReportsApi.downloadReport).toHaveBeenCalledWith(
        'inventory-valuation',
        'csv',
        'inventory-valuation.csv',
        {},
      ),
    );
  });

  it('disables downloads for product movement until a product is chosen', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);
    await screen.findByText('WIDGET-001');

    await user.click(screen.getByRole('tab', { name: 'Product Movement' }));

    expect(screen.getByRole('button', { name: /download csv/i })).toBeDisabled();
  });

  it('shows an error message when a report fails to load', async () => {
    mockedReportsApi.getInventoryValuation.mockRejectedValue(new Error('Network Error'));

    renderWithProviders(<ReportsPage />);

    expect(await screen.findByText('Failed to load report.')).toBeInTheDocument();
  });
});
