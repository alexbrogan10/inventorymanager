import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { Category } from '../categories/types';
import type { Supplier } from '../suppliers/types';
import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as productsApi from './api';
import { ProductDetailPage } from './ProductDetailPage';
import type { Product } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(productsApi);

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
  current_quantity: 50,
  minimum_quantity: 10,
  maximum_quantity: 200,
  warehouse_location: null,
  unit_type: 'each',
  image_url: null,
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
    mockedApi.getProduct.mockResolvedValue({ ...PRODUCT, current_quantity: 2 });

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
});
