import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as productsApi from '../products/api';
import type { PaginatedProducts, Product } from '../products/types';
import * as suppliersApi from '../suppliers/api';
import type { Supplier } from '../suppliers/types';
import * as warehousesApi from '../warehouses/api';
import type { Warehouse } from '../warehouses/types';
import * as purchaseOrdersApi from './api';
import { PurchaseOrdersPage } from './PurchaseOrdersPage';
import type { PurchaseOrder } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');
vi.mock('../suppliers/api');
vi.mock('../warehouses/api');
vi.mock('../products/api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(purchaseOrdersApi);
const mockedSuppliersApi = vi.mocked(suppliersApi);
const mockedWarehousesApi = vi.mocked(warehousesApi);
const mockedProductsApi = vi.mocked(productsApi);

beforeEach(() => {
  vi.clearAllMocks();
});

const MANAGER: User = {
  id: 1,
  email: 'manager@example.com',
  full_name: 'Manager User',
  role: 'manager',
  is_active: true,
  created_at: '',
};
const EMPLOYEE: User = { ...MANAGER, id: 2, email: 'employee@example.com', role: 'employee' };

const SUPPLIER: Supplier = {
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
};

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
  supplier: SUPPLIER,
  purchase_price: '5.00',
  selling_price: '9.99',
  total_quantity: 0,
  minimum_quantity: 0,
  maximum_quantity: null,
  unit_type: 'each',
  image_url: null,
  created_at: '',
  updated_at: '',
};

const SAMPLE_ORDER: PurchaseOrder = {
  id: 1,
  supplier: SUPPLIER,
  warehouse: WAREHOUSE,
  status: 'ordered',
  expected_delivery_date: null,
  notes: null,
  created_by_id: 1,
  items: [
    {
      id: 1,
      product: { id: 1, sku: 'WIDGET-001', name: 'Widget', unit_type: 'each' },
      quantity_ordered: 10,
      unit_cost: '4.25',
      quantity_received: 0,
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

describe('PurchaseOrdersPage', () => {
  it('renders purchase orders returned by the API', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listPurchaseOrders.mockResolvedValue({
      items: [SAMPLE_ORDER],
      total: 1,
      page: 1,
      page_size: 20,
    });

    renderPage(<PurchaseOrdersPage />);

    expect(await screen.findByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Acme Supply Co.')).toBeInTheDocument();
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getByText('Ordered')).toBeInTheDocument();
  });

  it('hides the create button for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listPurchaseOrders.mockResolvedValue({
      items: [SAMPLE_ORDER],
      total: 1,
      page: 1,
      page_size: 20,
    });

    renderPage(<PurchaseOrdersPage />);

    await screen.findByText('#1');
    expect(
      screen.queryByRole('button', { name: /create purchase order/i }),
    ).not.toBeInTheDocument();
  });

  it('lets a manager create a purchase order', async () => {
    mockAuth(MANAGER);
    mockedApi.listPurchaseOrders.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    mockedApi.createPurchaseOrder.mockResolvedValue({ ...SAMPLE_ORDER, id: 2 });
    mockedSuppliersApi.listSuppliers.mockResolvedValue([SUPPLIER]);
    mockedWarehousesApi.listWarehouses.mockResolvedValue([WAREHOUSE]);
    mockedProductsApi.listProducts.mockResolvedValue({
      items: [PRODUCT],
      total: 1,
      page: 1,
      page_size: 100,
    } satisfies PaginatedProducts);
    const user = userEvent.setup();

    renderPage(<PurchaseOrdersPage />);
    await user.click(await screen.findByRole('button', { name: /create purchase order/i }));

    const comboboxes = () => screen.getAllByRole('combobox');
    await user.click((await screen.findAllByRole('combobox'))[0]);
    await user.click(await screen.findByRole('option', { name: 'Acme Supply Co.' }));
    await user.click(comboboxes()[1]);
    await user.click(await screen.findByRole('option', { name: 'Main Warehouse' }));
    await user.click(comboboxes()[2]);
    await user.click(await screen.findByRole('option', { name: /WIDGET-001/ }));

    const quantityField = screen.getByLabelText(/quantity/i);
    await user.clear(quantityField);
    await user.type(quantityField, '20');
    const unitCostField = screen.getByLabelText(/unit cost/i);
    await user.clear(unitCostField);
    await user.type(unitCostField, '3.50');

    await user.click(screen.getByRole('button', { name: /^create$/i }));

    await waitFor(() =>
      expect(mockedApi.createPurchaseOrder.mock.calls[0]?.[0]).toEqual({
        supplier_id: 1,
        warehouse_id: 1,
        expected_delivery_date: null,
        notes: null,
        items: [{ product_id: 1, quantity_ordered: 20, unit_cost: '3.50' }],
      }),
    );
  });

  it('requests the next page when paginating', async () => {
    const user = userEvent.setup();
    mockAuth(EMPLOYEE);
    mockedApi.listPurchaseOrders.mockResolvedValue({
      items: [SAMPLE_ORDER],
      total: 50,
      page: 1,
      page_size: 20,
    });

    renderPage(<PurchaseOrdersPage />);
    await screen.findByText('#1');
    await user.click(screen.getByRole('button', { name: /next page/i }));

    await waitFor(() =>
      expect(mockedApi.listPurchaseOrders).toHaveBeenCalledWith({ page: 2, page_size: 20 }),
    );
  });

  it('requests a new page size and resets to the first page', async () => {
    const user = userEvent.setup();
    mockAuth(EMPLOYEE);
    mockedApi.listPurchaseOrders.mockResolvedValue({
      items: [SAMPLE_ORDER],
      total: 50,
      page: 1,
      page_size: 20,
    });

    renderPage(<PurchaseOrdersPage />);
    await screen.findByText('#1');
    await user.click(screen.getByRole('combobox', { name: /rows per page/i }));
    await user.click(await screen.findByRole('option', { name: '50' }));

    await waitFor(() =>
      expect(mockedApi.listPurchaseOrders).toHaveBeenCalledWith({ page: 1, page_size: 50 }),
    );
  });
});
