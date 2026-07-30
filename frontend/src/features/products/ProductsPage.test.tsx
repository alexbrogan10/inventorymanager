import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';
import * as categoriesApi from '../categories/api';
import * as suppliersApi from '../suppliers/api';
import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as productsApi from './api';
import { ProductsPage } from './ProductsPage';
import type { Product } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');
vi.mock('../categories/api');
vi.mock('../suppliers/api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedProductsApi = vi.mocked(productsApi);
const mockedCategoriesApi = vi.mocked(categoriesApi);
const mockedSuppliersApi = vi.mocked(suppliersApi);

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
    current_quantity: 50,
    minimum_quantity: 10,
    maximum_quantity: 200,
    warehouse_location: null,
    unit_type: 'each',
    image_url: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
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
  it('renders products with category/supplier names', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue([makeProduct()]);

    renderPage(<ProductsPage />);

    expect(await screen.findByText('WIDGET-001')).toBeInTheDocument();
    expect(screen.getByText('Widget')).toBeInTheDocument();
    expect(screen.getByText('Electronics')).toBeInTheDocument();
    expect(screen.getByText('Acme Supply Co.')).toBeInTheDocument();
  });

  it('shows a low stock chip when current quantity is below the minimum', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue([
      makeProduct({ current_quantity: 2, minimum_quantity: 10 }),
    ]);

    renderPage(<ProductsPage />);

    expect(await screen.findByText('Low stock')).toBeInTheDocument();
  });

  it('does not show a low stock chip when quantity is sufficient', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue([makeProduct({ current_quantity: 50 })]);

    renderPage(<ProductsPage />);

    await screen.findByText('WIDGET-001');
    expect(screen.queryByText('Low stock')).not.toBeInTheDocument();
  });

  it('hides write controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedProductsApi.listProducts.mockResolvedValue([makeProduct()]);

    renderPage(<ProductsPage />);

    await screen.findByText('WIDGET-001');
    expect(screen.queryByRole('button', { name: /add product/i })).not.toBeInTheDocument();
  });

  it('lets a manager create a product', async () => {
    mockAuth(MANAGER);
    mockedProductsApi.listProducts.mockResolvedValue([]);
    mockedProductsApi.createProduct.mockResolvedValue(makeProduct({ id: 2 }));
    mockedCategoriesApi.listCategories.mockResolvedValue([CATEGORY]);
    mockedSuppliersApi.listSuppliers.mockResolvedValue([SUPPLIER]);
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await user.click(await screen.findByRole('button', { name: /add product/i }));
    await user.type(screen.getByLabelText(/^sku/i), 'WIDGET-099');
    await user.type(screen.getByLabelText(/^name/i), 'New Widget');
    await user.click(await screen.findByLabelText(/category/i));
    await user.click(await screen.findByRole('option', { name: 'Electronics' }));
    await user.click(screen.getByLabelText(/supplier/i));
    await user.click(await screen.findByRole('option', { name: 'Acme Supply Co.' }));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

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
    mockedProductsApi.listProducts.mockResolvedValue([makeProduct()]);
    mockedProductsApi.deleteProduct.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderPage(<ProductsPage />);
    await user.click(await screen.findByLabelText(/delete widget/i));

    await waitFor(() => expect(mockedProductsApi.deleteProduct.mock.calls[0]?.[0]).toBe(1));
  });
});
