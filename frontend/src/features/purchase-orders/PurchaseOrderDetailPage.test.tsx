import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import type { Supplier } from '../suppliers/types';
import type { Warehouse } from '../warehouses/types';
import * as purchaseOrdersApi from './api';
import { PurchaseOrderDetailPage } from './PurchaseOrderDetailPage';
import type { PurchaseOrder } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(purchaseOrdersApi);

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

function makeOrder(overrides: Partial<PurchaseOrder> = {}): PurchaseOrder {
  return {
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

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/purchase-orders/1']}>
        <Routes>
          <Route path="/purchase-orders" element={<div>Purchase Orders List</div>} />
          <Route path="/purchase-orders/:id" element={<PurchaseOrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PurchaseOrderDetailPage', () => {
  it('renders order details and line items', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder());

    renderDetail();

    expect(await screen.findByText('Purchase Order #1')).toBeInTheDocument();
    expect(screen.getByText('Acme Supply Co.')).toBeInTheDocument();
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getByText(/WIDGET-001/)).toBeInTheDocument();
    expect(screen.getAllByText('Ordered').length).toBeGreaterThan(0);
  });

  it('hides ship/receive/cancel controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder());

    renderDetail();

    await screen.findByText('Purchase Order #1');
    expect(screen.queryByRole('button', { name: /^ship$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^receive$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^cancel$/i })).not.toBeInTheDocument();
  });

  it('lets a manager ship an ordered purchase order', async () => {
    mockAuth(MANAGER);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder({ status: 'ordered' }));
    mockedApi.shipPurchaseOrder.mockResolvedValue(makeOrder({ status: 'shipped' }));
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /^ship$/i }));

    await waitFor(() => expect(mockedApi.shipPurchaseOrder.mock.calls[0]?.[0]).toBe(1));
  });

  it('lets a manager receive a shipped purchase order', async () => {
    mockAuth(MANAGER);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder({ status: 'shipped' }));
    mockedApi.receivePurchaseOrder.mockResolvedValue(makeOrder({ status: 'received' }));
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /^receive$/i }));

    await waitFor(() => expect(mockedApi.receivePurchaseOrder.mock.calls[0]?.[0]).toBe(1));
  });

  it('lets a manager cancel an ordered purchase order after confirming', async () => {
    mockAuth(MANAGER);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder({ status: 'ordered' }));
    mockedApi.cancelPurchaseOrder.mockResolvedValue(makeOrder({ status: 'cancelled' }));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole('button', { name: /^cancel$/i }));

    await waitFor(() => expect(mockedApi.cancelPurchaseOrder.mock.calls[0]?.[0]).toBe(1));
  });

  it('shows no actions for a received purchase order', async () => {
    mockAuth(MANAGER);
    mockedApi.getPurchaseOrder.mockResolvedValue(makeOrder({ status: 'received' }));

    renderDetail();

    await screen.findByText('Purchase Order #1');
    expect(screen.queryByRole('button', { name: /^ship$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^receive$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^cancel$/i })).not.toBeInTheDocument();
  });
});
