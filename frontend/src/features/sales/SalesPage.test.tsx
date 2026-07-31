import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as productsApi from '../products/api';
import type { PaginatedProducts, Product } from '../products/types';
import * as warehousesApi from '../warehouses/api';
import type { Warehouse } from '../warehouses/types';
import * as salesApi from './api';
import { SalesPage } from './SalesPage';
import type { Sale } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');
vi.mock('../warehouses/api');
vi.mock('../products/api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(salesApi);
const mockedWarehousesApi = vi.mocked(warehousesApi);
const mockedProductsApi = vi.mocked(productsApi);

const MANAGER: User = {
  id: 1,
  email: 'manager@example.com',
  full_name: 'Manager User',
  role: 'manager',
  is_active: true,
  created_at: '',
};
const EMPLOYEE: User = { ...MANAGER, id: 2, email: 'employee@example.com', role: 'employee' };

const WAREHOUSE: Warehouse = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: null,
  created_at: '',
  updated_at: '',
};

const PRODUCT: Product = {
  id: 1,
  sku: 'WIDGET-001',
  barcode: null,
  name: 'Widget',
  description: null,
  category_id: 1,
  supplier_id: 1,
  category: { id: 1, name: 'Electronics', description: null, created_at: '', updated_at: '' },
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
  total_quantity: 20,
  minimum_quantity: 0,
  maximum_quantity: null,
  unit_type: 'each',
  image_url: null,
  created_at: '',
  updated_at: '',
};

const SAMPLE_SALE: Sale = {
  id: 1,
  warehouse: WAREHOUSE,
  customer_name: 'Jane Customer',
  customer_email: 'jane.customer@example.com',
  customer_phone: '555-0001',
  notes: null,
  sold_by_id: 1,
  items: [
    {
      id: 1,
      product: { id: 1, sku: 'WIDGET-001', name: 'Widget', unit_type: 'each' },
      quantity: 3,
      unit_price: '9.99',
    },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function mockAuth(user: User) {
  mockedUseAuth.mockReturnValue({
    user,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderPage(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SalesPage', () => {
  it('renders sales returned by the API with a computed total', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listSales.mockResolvedValue([SAMPLE_SALE]);

    renderPage(<SalesPage />);

    expect(await screen.findByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Jane Customer')).toBeInTheDocument();
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getByText('$29.97')).toBeInTheDocument();
  });

  it('hides the record sale button for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listSales.mockResolvedValue([SAMPLE_SALE]);

    renderPage(<SalesPage />);

    await screen.findByText('#1');
    expect(screen.queryByRole('button', { name: /record sale/i })).not.toBeInTheDocument();
  });

  it('lets a manager record a sale with an auto-filled unit price', async () => {
    mockAuth(MANAGER);
    mockedApi.listSales.mockResolvedValue([]);
    mockedApi.createSale.mockResolvedValue({ ...SAMPLE_SALE, id: 2 });
    mockedWarehousesApi.listWarehouses.mockResolvedValue([WAREHOUSE]);
    mockedProductsApi.listProducts.mockResolvedValue({
      items: [PRODUCT],
      total: 1,
      page: 1,
      page_size: 100,
    } satisfies PaginatedProducts);
    const user = userEvent.setup();

    renderPage(<SalesPage />);
    await user.click(await screen.findByRole('button', { name: /record sale/i }));

    const comboboxes = () => screen.getAllByRole('combobox');
    await user.click((await screen.findAllByRole('combobox'))[0]);
    await user.click(await screen.findByRole('option', { name: 'Main Warehouse' }));
    await user.type(screen.getByLabelText(/customer name/i), 'John Buyer');
    await user.click(comboboxes()[1]);
    await user.click(await screen.findByRole('option', { name: /WIDGET-001/ }));

    const quantityField = screen.getByLabelText(/quantity/i);
    await user.clear(quantityField);
    await user.type(quantityField, '4');

    await user.click(screen.getByRole('button', { name: /^record sale$/i }));

    await waitFor(() =>
      expect(mockedApi.createSale.mock.calls[0]?.[0]).toEqual({
        warehouse_id: 1,
        customer_name: 'John Buyer',
        customer_email: null,
        customer_phone: null,
        notes: null,
        items: [{ product_id: 1, quantity: 4, unit_price: '9.99' }],
      }),
    );
  });
});
