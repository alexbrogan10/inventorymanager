import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';
import * as warehousesApi from '../warehouses/api';
import type { Warehouse } from '../warehouses/types';
import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as forecastingApi from '../forecasting/api';
import * as productsApi from './api';
import { ProductDetailPage } from './ProductDetailPage';
import type { InventoryLevel, Product } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');
vi.mock('../warehouses/api');
vi.mock('../forecasting/api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(productsApi);
const mockedWarehousesApi = vi.mocked(warehousesApi);
const mockedForecastingApi = vi.mocked(forecastingApi);

const MANAGER: User = {
  id: 1,
  email: 'manager@example.com',
  full_name: 'Manager User',
  role: 'manager',
  is_active: true,
  created_at: '',
};
const EMPLOYEE: User = { ...MANAGER, id: 2, email: 'employee@example.com', role: 'employee' };

const CATEGORY: Category = {
  id: 1,
  name: 'Electronics',
  description: null,
  created_at: '',
  updated_at: '',
};
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

const PRODUCT: Product = {
  id: 1,
  sku: 'WIDGET-001',
  barcode: null,
  name: 'Widget',
  description: 'A fine widget',
  category_id: 1,
  supplier_id: 1,
  category: CATEGORY,
  supplier: SUPPLIER,
  purchase_price: '5.00',
  selling_price: '9.99',
  total_quantity: 50,
  minimum_quantity: 10,
  maximum_quantity: 200,
  unit_type: 'each',
  image_url: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const WAREHOUSE: Warehouse = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const EAST_WAREHOUSE: Warehouse = {
  id: 2,
  name: 'East Warehouse',
  address: '2 East St',
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const INVENTORY_LEVELS: InventoryLevel[] = [{ warehouse: WAREHOUSE, quantity: 50 }];

function mockAuth(user: User) {
  mockedUseAuth.mockReturnValue({
    user,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/products/1']}>
        <Routes>
          <Route path="/products" element={<div>Products List</div>} />
          <Route path="/products/:id" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProductDetailPage', () => {
  beforeEach(() => {
    mockedApi.getProductInventory.mockResolvedValue(INVENTORY_LEVELS);
    mockedForecastingApi.predictProductDemand.mockRejectedValue(new Error('not under test here'));
  });

  it('renders the product details', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);

    renderDetail();

    expect(await screen.findByText('Widget')).toBeInTheDocument();
    expect(screen.getByText(/SKU: WIDGET-001/)).toBeInTheDocument();
    expect(screen.getByText('Electronics')).toBeInTheDocument();
    expect(screen.getByText('Acme Supply Co.')).toBeInTheDocument();
  });

  it('hides edit/delete controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);

    renderDetail();

    await screen.findByText('Widget');
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('shows a low stock chip when under the minimum quantity', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getProduct.mockResolvedValue({ ...PRODUCT, total_quantity: 2 });

    renderDetail();

    expect(await screen.findByText('Low stock')).toBeInTheDocument();
  });

  it('deletes the product and navigates back to the list after confirming', async () => {
    mockAuth(MANAGER);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);
    mockedApi.deleteProduct.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /delete/i }));

    await waitFor(() => expect(mockedApi.deleteProduct.mock.calls[0]?.[0]).toBe(1));
    expect(await screen.findByText('Products List')).toBeInTheDocument();
  });

  it('shows the inventory breakdown by warehouse', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);

    renderDetail();

    expect(await screen.findByText('Inventory by warehouse')).toBeInTheDocument();
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getAllByText('50')).toHaveLength(2);
  });

  it('hides adjust/transfer stock controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);

    renderDetail();

    await screen.findByText('Inventory by warehouse');
    expect(screen.queryByRole('button', { name: /adjust stock/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /transfer stock/i })).not.toBeInTheDocument();
  });

  it('lets a manager adjust the stock level at a warehouse', async () => {
    mockAuth(MANAGER);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);
    mockedApi.setProductInventoryLevel.mockResolvedValue([{ warehouse: WAREHOUSE, quantity: 75 }]);
    mockedWarehousesApi.listWarehouses.mockResolvedValue([WAREHOUSE, EAST_WAREHOUSE]);
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /adjust stock/i }));
    await user.click(await screen.findByLabelText(/warehouse/i));
    await user.click(await screen.findByRole('option', { name: 'Main Warehouse' }));
    const quantityField = screen.getByLabelText(/new quantity/i);
    await user.clear(quantityField);
    await user.type(quantityField, '75');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() =>
      expect(mockedApi.setProductInventoryLevel.mock.calls[0]).toEqual([1, 1, 75]),
    );
  });

  it('lets a manager transfer stock between warehouses', async () => {
    mockAuth(MANAGER);
    mockedApi.getProduct.mockResolvedValue(PRODUCT);
    mockedApi.transferProductInventory.mockResolvedValue([
      { warehouse: WAREHOUSE, quantity: 40 },
      { warehouse: EAST_WAREHOUSE, quantity: 10 },
    ]);
    mockedWarehousesApi.listWarehouses.mockResolvedValue([WAREHOUSE, EAST_WAREHOUSE]);
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /transfer stock/i }));
    await user.click(await screen.findByLabelText(/from warehouse/i));
    await user.click(await screen.findByRole('option', { name: /main warehouse/i }));
    await user.click(screen.getByLabelText(/to warehouse/i));
    await user.click(await screen.findByRole('option', { name: 'East Warehouse' }));
    const quantityField = screen.getByLabelText(/^quantity/i);
    await user.clear(quantityField);
    await user.type(quantityField, '10');
    await user.click(screen.getByRole('button', { name: /^transfer$/i }));

    await waitFor(() => expect(mockedApi.transferProductInventory.mock.calls[0]?.[0]).toBe(1));
    expect(mockedApi.transferProductInventory.mock.calls[0]?.[1]).toEqual({
      from_warehouse_id: 1,
      to_warehouse_id: 2,
      quantity: 10,
    });
  });
});
