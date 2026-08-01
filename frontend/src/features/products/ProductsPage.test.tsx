import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';
import * as categoriesApi from '../categories/api';
import * as suppliersApi from '../suppliers/api';
import * as warehousesApi from '../warehouses/api';
import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as productsApi from './api';
import { ProductsPage } from './ProductsPage';
import type { PaginatedProducts, Product } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');
vi.mock('../categories/api');
vi.mock('../suppliers/api');
vi.mock('../warehouses/api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedProductsApi = vi.mocked(productsApi);
const mockedCategoriesApi = vi.mocked(categoriesApi);
const mockedSuppliersApi = vi.mocked(suppliersApi);
const mockedWarehousesApi = vi.mocked(warehousesApi);

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

function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 1,
    sku: 'WIDGET-001',
    barcode: null,
    name: 'Widget',
    description: null,
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
    ...overrides,
  };
}

function makePaginated(items: Product[]): PaginatedProducts {
  return { items, total: items.length, page: 1, page_size: 20 };
}

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

describe('ProductsPage', () => {
  beforeEach(() => {
    mockedWarehousesApi.listWarehouses.mockResolvedValue([]);
  });

  it('renders products with category/supplier names', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([makeProduct()]));

    renderPage(<ProductsPage />);

    expect(await screen.findByText('WIDGET-001')).toBeInTheDocument();
    expect(screen.getByText('Widget')).toBeInTheDocument();
    expect(screen.getByText('Electronics')).toBeInTheDocument();
    expect(screen.getByText('Acme Supply Co.')).toBeInTheDocument();
  });

  it('shows a low stock chip when current quantity is below the minimum', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue(
      makePaginated([makeProduct({ total_quantity: 2, minimum_quantity: 10 })]),
    );

    renderPage(<ProductsPage />);

    expect(await screen.findByText('Low stock')).toBeInTheDocument();
  });

  it('does not show a low stock chip when quantity is sufficient', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue(
      makePaginated([makeProduct({ total_quantity: 50 })]),
    );

    renderPage(<ProductsPage />);

    await screen.findByText('WIDGET-001');
    expect(screen.queryByText('Low stock')).not.toBeInTheDocument();
  });

  it('hides write controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([makeProduct()]));

    renderPage(<ProductsPage />);

    await screen.findByText('WIDGET-001');
    expect(screen.queryByRole('button', { name: /add product/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /import csv/i })).not.toBeInTheDocument();
  });

  it('navigates to the import page when a manager clicks Import CSV', async () => {
    mockAuth(MANAGER);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([]));
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<ProductsPage />} />
            <Route path="/products/import" element={<div>Import Page Placeholder</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole('button', { name: /import csv/i }));

    expect(await screen.findByText('Import Page Placeholder')).toBeInTheDocument();
  });

  it('lets a manager create a product', async () => {
    mockAuth(MANAGER);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([]));
    mockedProductsApi.createProduct.mockResolvedValue(makeProduct({ id: 2 }));
    mockedCategoriesApi.listCategories.mockResolvedValue([CATEGORY]);
    mockedSuppliersApi.listSuppliers.mockResolvedValue([SUPPLIER]);
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await user.click(await screen.findByRole('button', { name: /add product/i }));
    const dialog = within(await screen.findByRole('dialog'));
    await user.type(dialog.getByLabelText(/^sku/i), 'WIDGET-099');
    await user.type(dialog.getByLabelText(/^name/i), 'New Widget');
    await user.click(await dialog.findByLabelText(/category/i));
    await user.click(await screen.findByRole('option', { name: 'Electronics' }));
    await user.click(dialog.getByLabelText(/supplier/i));
    await user.click(await screen.findByRole('option', { name: 'Acme Supply Co.' }));
    await user.click(dialog.getByRole('button', { name: /^save$/i }));

    await waitFor(() =>
      expect(mockedProductsApi.createProduct.mock.calls[0]?.[0]).toEqual(
        expect.objectContaining({
          sku: 'WIDGET-099',
          name: 'New Widget',
          category_id: 1,
          supplier_id: 1,
        }),
      ),
    );
  });

  it('lets a manager delete a product after confirming', async () => {
    mockAuth(MANAGER);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([makeProduct()]));
    mockedProductsApi.deleteProduct.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await user.click(await screen.findByLabelText(/delete widget/i));

    await waitFor(() => expect(mockedProductsApi.deleteProduct.mock.calls[0]?.[0]).toBe(1));
  });

  it('refetches with the selected category filter', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue(makePaginated([makeProduct()]));
    mockedCategoriesApi.listCategories.mockResolvedValue([CATEGORY]);
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await screen.findByText('WIDGET-001');
    await user.click(screen.getByLabelText(/^category$/i));
    await user.click(await screen.findByRole('option', { name: 'Electronics' }));

    await waitFor(() =>
      expect(mockedProductsApi.listProducts).toHaveBeenLastCalledWith(
        expect.objectContaining({ category_id: 1, page: 1 }),
      ),
    );
  });

  it('requests the next page when paginating forward', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue({
      items: [makeProduct()],
      total: 50,
      page: 1,
      page_size: 20,
    });
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await screen.findByText('WIDGET-001');
    await user.click(screen.getByRole('button', { name: /next page/i }));

    await waitFor(() =>
      expect(mockedProductsApi.listProducts).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2 }),
      ),
    );
  });
});
